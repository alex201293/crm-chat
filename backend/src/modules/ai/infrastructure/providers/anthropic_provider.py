"""Anthropic (Claude) provider implementation."""

from typing import AsyncIterator

import anthropic
import structlog

from src.config.settings import get_settings
from src.modules.ai.domain.interfaces import (
    AIProvider,
    CompletionConfig,
    CompletionResult,
    ILLMProvider,
)

logger = structlog.get_logger()


class AnthropicProvider(ILLMProvider):
    """Anthropic Claude API implementation."""

    # Map generic model names to Anthropic model IDs
    MODEL_MAP = {
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-haiku": "claude-haiku-4-20250514",
        "claude-opus": "claude-opus-4-20250514",
    }

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.ai.ANTHROPIC_API_KEY
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.ANTHROPIC

    async def complete(self, prompt: str, config: CompletionConfig) -> CompletionResult:
        model = self.MODEL_MAP.get(config.model, config.model)
        system_prompt = self._build_system_prompt(config)

        messages = self._build_messages(prompt, config)

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=system_prompt,
                messages=messages,
                stop_sequences=config.stop_sequences or None,
            )
        except anthropic.APIError as e:
            logger.error("Anthropic API error", error=str(e), model=model)
            raise

        content = ""
        if response.content:
            content = response.content[0].text

        return CompletionResult(
            content=content,
            model=response.model,
            provider=AIProvider.ANTHROPIC,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason or "end_turn",
        )

    async def stream(
        self, prompt: str, config: CompletionConfig
    ) -> AsyncIterator[str]:
        model = self.MODEL_MAP.get(config.model, config.model)
        system_prompt = self._build_system_prompt(config)
        messages = self._build_messages(prompt, config)

        async with self._client.messages.stream(
            model=model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_system_prompt(self, config: CompletionConfig) -> str:
        parts = []
        if config.system_prompt:
            parts.append(config.system_prompt)

        if config.context_documents:
            context_text = "\n\n---\n\n".join(config.context_documents)
            parts.append(
                f"Use the following context to answer the user's question. "
                f"If the answer is not in the context, say so clearly.\n\n"
                f"CONTEXT:\n{context_text}"
            )

        return "\n\n".join(parts) if parts else ""

    def _build_messages(
        self, prompt: str, config: CompletionConfig
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        for msg in config.conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": prompt})
        return messages
