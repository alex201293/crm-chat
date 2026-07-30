"""Mistral AI provider implementation."""

from typing import AsyncIterator

from mistralai import Mistral
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


class MistralProvider(ILLMProvider, IEmbeddingProvider):
    """Mistral AI API implementation."""

    MODEL_MAP = {
        "mistral-large": "mistral-large-latest",
        "mistral-medium": "mistral-medium-latest",
        "mistral-small": "mistral-small-latest",
    }

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.ai.MISTRAL_API_KEY
        self._client = Mistral(api_key=self._api_key) if self._api_key else None

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.MISTRAL

    @property
    def dimensions(self) -> int:
        return 1024  # mistral-embed

    async def complete(self, prompt: str, config: CompletionConfig) -> CompletionResult:
        if not self._client:
            raise RuntimeError("Mistral API key not configured")

        model = self.MODEL_MAP.get(config.model, config.model)
        messages = self._build_messages(prompt, config)

        try:
            response = await self._client.chat.complete_async(
                model=model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                stop=config.stop_sequences or None,
            )
        except Exception as e:
            logger.error("Mistral API error", error=str(e), model=model)
            raise

        choice = response.choices[0]
        usage = response.usage

        return CompletionResult(
            content=choice.message.content or "",
            model=response.model,
            provider=AIProvider.MISTRAL,
            tokens_used=usage.total_tokens if usage else 0,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(
        self, prompt: str, config: CompletionConfig
    ) -> AsyncIterator[str]:
        if not self._client:
            raise RuntimeError("Mistral API key not configured")

        model = self.MODEL_MAP.get(config.model, config.model)
        messages = self._build_messages(prompt, config)

        response = await self._client.chat.stream_async(
            model=model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        async for event in response:
            if event.data.choices and event.data.choices[0].delta.content:
                yield event.data.choices[0].delta.content

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        if not self._client:
            raise RuntimeError("Mistral API key not configured")

        response = await self._client.embeddings.create_async(
            model="mistral-embed",
            inputs=texts,
        )

        embeddings = [item.embedding for item in response.data]

        return EmbeddingResult(
            embeddings=embeddings,
            model="mistral-embed",
            provider=AIProvider.MISTRAL,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            dimensions=self.dimensions,
        )

    async def embed_single(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result.embeddings[0]

    async def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_messages(
        self, prompt: str, config: CompletionConfig
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        system_parts = []
        if config.system_prompt:
            system_parts.append(config.system_prompt)
        if config.context_documents:
            context_text = "\n\n---\n\n".join(config.context_documents)
            system_parts.append(f"CONTEXT:\n{context_text}")

        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        for msg in config.conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": prompt})
        return messages
