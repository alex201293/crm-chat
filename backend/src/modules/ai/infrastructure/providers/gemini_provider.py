"""Google Gemini provider implementation."""

from typing import AsyncIterator

import google.generativeai as genai
import structlog

from src.config.settings import get_settings
from src.modules.ai.domain.interfaces import (
    AIProvider,
    CompletionConfig,
    CompletionResult,
    EmbeddingResult,
    IEmbeddingProvider,
    ILLMProvider,
)

logger = structlog.get_logger()


class GeminiProvider(ILLMProvider, IEmbeddingProvider):
    """Google Gemini API implementation."""

    MODEL_MAP = {
        "gemini-pro": "gemini-1.5-pro",
        "gemini-flash": "gemini-1.5-flash",
    }

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.ai.GOOGLE_AI_API_KEY
        if self._api_key:
            genai.configure(api_key=self._api_key)

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.GOOGLE

    @property
    def dimensions(self) -> int:
        return 768  # text-embedding-004

    async def complete(self, prompt: str, config: CompletionConfig) -> CompletionResult:
        model_name = self.MODEL_MAP.get(config.model, config.model)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self._build_system_prompt(config) or None,
        )

        # Build chat history
        history = []
        for msg in config.conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history)

        try:
            response = await chat.send_message_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=config.temperature,
                    max_output_tokens=config.max_tokens,
                    top_p=config.top_p,
                    stop_sequences=config.stop_sequences or None,
                ),
            )
        except Exception as e:
            logger.error("Gemini API error", error=str(e), model=model_name)
            raise

        # Estimate tokens (Gemini doesn't always return exact counts)
        content = response.text or ""
        prompt_tokens = len(prompt.split()) * 2  # rough estimate
        completion_tokens = len(content.split()) * 2

        return CompletionResult(
            content=content,
            model=model_name,
            provider=AIProvider.GOOGLE,
            tokens_used=prompt_tokens + completion_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason="stop",
        )

    async def stream(
        self, prompt: str, config: CompletionConfig
    ) -> AsyncIterator[str]:
        model_name = self.MODEL_MAP.get(config.model, config.model)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self._build_system_prompt(config) or None,
        )

        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            ),
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
        )

        embeddings = result["embedding"] if isinstance(result["embedding"][0], list) else [result["embedding"]]

        return EmbeddingResult(
            embeddings=embeddings,
            model="text-embedding-004",
            provider=AIProvider.GOOGLE,
            tokens_used=sum(len(t.split()) for t in texts),
            dimensions=self.dimensions,
        )

    async def embed_single(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result.embeddings[0]

    async def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_system_prompt(self, config: CompletionConfig) -> str:
        parts = []
        if config.system_prompt:
            parts.append(config.system_prompt)
        if config.context_documents:
            context_text = "\n\n---\n\n".join(config.context_documents)
            parts.append(f"CONTEXT:\n{context_text}")
        return "\n\n".join(parts)
