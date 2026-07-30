"""
Groq provider - FREE tier, OpenAI-compatible API.
Uses Llama, Mixtral, and Gemma models on Groq's fast inference.
No credit card required. Get key at: https://console.groq.com
"""

from typing import AsyncIterator

import httpx
import structlog

from src.modules.ai.domain.interfaces import (
    AIProvider,
    CompletionConfig,
    CompletionResult,
    ILLMProvider,
)

logger = structlog.get_logger()

GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqProvider(ILLMProvider):
    """
    Groq API - OpenAI-compatible format.
    Free tier: 30 req/min, no credit card needed.
    Models: llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it
    """

    MODEL_MAP = {
        "groq-llama": "llama-3.3-70b-versatile",
        "groq-mixtral": "mixtral-8x7b-32768",
        "groq-gemma": "gemma2-9b-it",
    }

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=GROQ_API_BASE,
            timeout=30.0,
        )

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.OPENAI  # Compatible format

    async def complete(self, prompt: str, config: CompletionConfig) -> CompletionResult:
        model = self.MODEL_MAP.get(config.model, "llama-3.3-70b-versatile")
        messages = self._build_messages(prompt, config)

        response = await self._client.post(
            "/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
                "stream": False,
            },
        )

        if response.status_code != 200:
            error = response.json().get("error", {})
            logger.error("Groq API error", status=response.status_code, error=error)
            raise RuntimeError(f"Groq error: {error.get('message', response.status_code)}")

        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return CompletionResult(
            content=choice["message"]["content"] or "",
            model=data.get("model", model),
            provider=AIProvider.OPENAI,
            tokens_used=usage.get("total_tokens", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def stream(self, prompt: str, config: CompletionConfig) -> AsyncIterator[str]:
        model = self.MODEL_MAP.get(config.model, "llama-3.3-70b-versatile")
        messages = self._build_messages(prompt, config)

        async with self._client.stream(
            "POST",
            "/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stream": True,
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    import json
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        yield delta["content"]

    async def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_messages(self, prompt: str, config: CompletionConfig) -> list[dict]:
        messages: list[dict] = []

        system_parts = []
        if config.system_prompt:
            system_parts.append(config.system_prompt)
        if config.context_documents:
            context = "\n\n---\n\n".join(config.context_documents)
            system_parts.append(f"CONTEXT:\n{context}")

        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        for msg in config.conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": prompt})
        return messages
