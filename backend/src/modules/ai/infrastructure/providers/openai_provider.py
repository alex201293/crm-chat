"""OpenAI provider implementation (GPT-4o, GPT-4, GPT-3.5, embeddings)."""

from typing import AsyncIterator

import openai
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


class OpenAIProvider(ILLMProvider, IEmbeddingProvider):
    """OpenAI API implementation for chat completions and embeddings."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.ai.OPENAI_API_KEY
        self._client = openai.AsyncOpenAI(api_key=self._api_key)

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.OPENAI

    @property
    def dimensions(self) -> int:
        return 1536  # text-embedding-ada-002 / text-embedding-3-small

    async def complete(self, prompt: str, config: CompletionConfig) -> CompletionResult:
        messages = self._build_messages(prompt, config)

        try:
            response = await self._client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                stop=config.stop_sequences or None,
            )
        except openai.APIError as e:
            logger.error("OpenAI API error", error=str(e), model=config.model)
            raise

        choice = response.choices[0]
        usage = response.usage

        return CompletionResult(
            content=choice.message.content or "",
            model=response.model,
            provider=AIProvider.OPENAI,
            tokens_used=(usage.total_tokens if usage else 0),
            prompt_tokens=(usage.prompt_tokens if usage else 0),
            completion_tokens=(usage.completion_tokens if usage else 0),
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(
        self, prompt: str, config: CompletionConfig
    ) -> AsyncIterator[str]:
        messages = self._build_messages(prompt, config)

        stream = await self._client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            stop=config.stop_sequences or None,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        response = await self._client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )

        embeddings = [item.embedding for item in response.data]

        return EmbeddingResult(
            embeddings=embeddings,
            model="text-embedding-3-small",
            provider=AIProvider.OPENAI,
            tokens_used=response.usage.total_tokens,
            dimensions=len(embeddings[0]) if embeddings else self.dimensions,
        )

    async def embed_single(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result.embeddings[0]

    async def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_messages(
        self, prompt: str, config: CompletionConfig
    ) -> list[dict[str, str]]:
        """Build OpenAI chat messages from config."""
        messages: list[dict[str, str]] = []

        # System prompt
        system_parts = []
        if config.system_prompt:
            system_parts.append(config.system_prompt)

        # RAG context injection
        if config.context_documents:
            context_text = "\n\n---\n\n".join(config.context_documents)
            system_parts.append(
                f"Use the following context to answer the user's question. "
                f"If the answer is not in the context, say so clearly.\n\n"
                f"CONTEXT:\n{context_text}"
            )

        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        # Conversation history
        for msg in config.conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Current user message
        messages.append({"role": "user", "content": prompt})

        return messages
