"""
AI Service - orchestrates LLM provider selection, fallback, and response generation.
This is the main entry point for all AI operations in the application.
"""

from typing import AsyncIterator

import structlog

from src.config.settings import get_settings
from src.modules.ai.domain.interfaces import (
    AIProvider,
    CompletionConfig,
    CompletionResult,
    ILLMProvider,
)
from src.modules.ai.infrastructure.providers import (
    AnthropicProvider,
    GeminiProvider,
    MistralProvider,
    OpenAIProvider,
)

logger = structlog.get_logger()


class AIService:
    """
    High-level AI service that manages provider selection and failover.

    Features:
    - Provider selection based on tenant configuration
    - Automatic fallback to alternative providers on failure
    - Confidence scoring for escalation decisions
    - Conversation context management
    """

    def __init__(self, tenant_settings: dict | None = None) -> None:
        self._settings = get_settings()
        self._tenant_settings = tenant_settings or {}
        self._providers: dict[AIProvider, ILLMProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize all configured providers."""
        # Groq (free tier) - registers as OPENAI since it's compatible
        groq_key = self._settings.ai.GROQ_API_KEY
        if groq_key:
            from src.modules.ai.infrastructure.providers.groq_provider import GroqProvider
            self._providers[AIProvider.OPENAI] = GroqProvider(api_key=groq_key)

        # OpenAI (overrides Groq if both present)
        if self._settings.ai.OPENAI_API_KEY and OpenAIProvider:
            self._providers[AIProvider.OPENAI] = OpenAIProvider()
        if self._settings.ai.ANTHROPIC_API_KEY and AnthropicProvider:
            self._providers[AIProvider.ANTHROPIC] = AnthropicProvider()
        if self._settings.ai.GOOGLE_AI_API_KEY and GeminiProvider:
            self._providers[AIProvider.GOOGLE] = GeminiProvider()
        if self._settings.ai.MISTRAL_API_KEY and MistralProvider:
            self._providers[AIProvider.MISTRAL] = MistralProvider()

    def _get_preferred_provider(self) -> AIProvider:
        """Get the preferred provider from tenant settings or global default."""
        tenant_provider = self._tenant_settings.get("ai_provider")
        if tenant_provider:
            try:
                return AIProvider(tenant_provider)
            except ValueError:
                pass
        return AIProvider(self._settings.ai.DEFAULT_AI_PROVIDER)

    def _get_preferred_model(self) -> str:
        """Get the preferred model from tenant settings or global default."""
        return self._tenant_settings.get("ai_model") or self._settings.ai.DEFAULT_AI_MODEL

    def _get_fallback_order(self, primary: AIProvider) -> list[AIProvider]:
        """Get fallback provider order, excluding the primary."""
        all_providers = [AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.GOOGLE, AIProvider.MISTRAL]
        return [p for p in all_providers if p != primary and p in self._providers]

    async def generate_response(
        self,
        user_message: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        context_documents: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        """
        Generate an AI response with automatic fallback.

        Args:
            user_message: The user's message to respond to
            system_prompt: System instructions for the AI
            conversation_history: Previous messages for context
            context_documents: RAG context documents
            temperature: Creativity parameter (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum response length

        Returns:
            CompletionResult with the AI's response and metadata
        """
        preferred = self._get_preferred_provider()
        model = self._get_preferred_model()

        config = CompletionConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            conversation_history=conversation_history or [],
            context_documents=context_documents or [],
        )

        # Try preferred provider first
        if preferred in self._providers:
            try:
                result = await self._providers[preferred].complete(user_message, config)
                result.confidence_score = self._estimate_confidence(result)
                return result
            except Exception as e:
                logger.warning(
                    "Primary AI provider failed, trying fallback",
                    provider=preferred.value,
                    error=str(e),
                )

        # Try fallback providers
        for fallback_provider in self._get_fallback_order(preferred):
            try:
                result = await self._providers[fallback_provider].complete(
                    user_message, config
                )
                result.confidence_score = self._estimate_confidence(result)
                logger.info(
                    "Used fallback AI provider",
                    provider=fallback_provider.value,
                )
                return result
            except Exception as e:
                logger.warning(
                    "Fallback provider failed",
                    provider=fallback_provider.value,
                    error=str(e),
                )
                continue

        # All providers failed
        raise RuntimeError("All AI providers are unavailable")

    async def stream_response(
        self,
        user_message: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        context_documents: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Stream an AI response token by token."""
        preferred = self._get_preferred_provider()
        model = self._get_preferred_model()

        config = CompletionConfig(
            model=model,
            system_prompt=system_prompt,
            conversation_history=conversation_history or [],
            context_documents=context_documents or [],
        )

        provider = self._providers.get(preferred)
        if not provider:
            # Use first available
            if not self._providers:
                raise RuntimeError("No AI providers configured")
            provider = next(iter(self._providers.values()))

        async for token in provider.stream(user_message, config):
            yield token

    def _estimate_confidence(self, result: CompletionResult) -> float:
        """
        Estimate response confidence based on heuristics.
        Used for escalation decisions.

        Low confidence triggers:
        - Very short responses (might indicate uncertainty)
        - Content filter triggered
        - Response contains hedging language
        """
        score = 1.0

        # Short responses indicate possible uncertainty
        word_count = len(result.content.split())
        if word_count < 5:
            score -= 0.3

        # Content filter
        if result.finish_reason == "content_filter":
            score -= 0.5

        # Hedging language detection
        hedging_phrases = [
            "i'm not sure",
            "i don't know",
            "i cannot",
            "i can't help",
            "no tengo información",
            "no puedo ayudar",
            "no estoy seguro",
            "no sé",
            "contactar a un agente",
            "hablar con un humano",
        ]
        lower_content = result.content.lower()
        for phrase in hedging_phrases:
            if phrase in lower_content:
                score -= 0.3
                break

        # Truncated response
        if result.finish_reason == "length":
            score -= 0.2

        return max(0.0, min(1.0, score))

    def should_escalate(self, confidence: float, message_content: str = "") -> bool:
        """
        Determine if a conversation should be escalated to a human agent.

        Escalation triggers:
        - Low AI confidence (< 0.5)
        - Explicit user request for human agent
        - Anger/frustration detection
        - Complaint keywords
        """
        # Low confidence
        if confidence < 0.5:
            return True

        # Explicit escalation request
        escalation_keywords = [
            "hablar con un agente",
            "hablar con un humano",
            "quiero un agente",
            "talk to a human",
            "talk to an agent",
            "speak to someone",
            "real person",
            "persona real",
            "agente humano",
        ]
        lower_msg = message_content.lower()
        for keyword in escalation_keywords:
            if keyword in lower_msg:
                return True

        # Complaint/frustration detection
        frustration_keywords = [
            "esto es inaceptable",
            "quiero quejarme",
            "reclamación",
            "esto no funciona",
            "pésimo servicio",
            "unacceptable",
            "complaint",
            "terrible service",
            "i want to complain",
        ]
        for keyword in frustration_keywords:
            if keyword in lower_msg:
                return True

        return False
