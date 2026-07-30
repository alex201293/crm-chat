"""
LLM Provider abstraction layer.
Defines the contract that all AI providers must implement.
Allows swapping providers without changing business logic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Protocol


class AIProvider(str, Enum):
    """Supported AI providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"


@dataclass
class CompletionConfig:
    """Configuration for a completion request."""

    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 1.0
    stop_sequences: list[str] = field(default_factory=list)
    system_prompt: str = ""
    # RAG context to inject
    context_documents: list[str] = field(default_factory=list)
    # Conversation history for multi-turn
    conversation_history: list[dict[str, str]] = field(default_factory=list)


@dataclass
class CompletionResult:
    """Result of a completion request."""

    content: str
    model: str
    provider: AIProvider
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str  # "stop", "length", "content_filter"
    confidence_score: float = 1.0  # 0.0 to 1.0, estimated by response quality


@dataclass
class EmbeddingResult:
    """Result of an embedding request."""

    embeddings: list[list[float]]
    model: str
    provider: AIProvider
    tokens_used: int
    dimensions: int


class ILLMProvider(Protocol):
    """
    Port for LLM providers.
    Each provider (OpenAI, Claude, Gemini, Mistral) implements this protocol.
    """

    @property
    def provider_name(self) -> AIProvider: ...

    async def complete(self, prompt: str, config: CompletionConfig) -> CompletionResult:
        """Generate a completion for the given prompt."""
        ...

    async def stream(
        self, prompt: str, config: CompletionConfig
    ) -> AsyncIterator[str]:
        """Stream a completion token by token."""
        ...

    async def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        ...


class IEmbeddingProvider(Protocol):
    """Port for embedding providers (used by RAG)."""

    @property
    def provider_name(self) -> AIProvider: ...

    @property
    def dimensions(self) -> int: ...

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings for a list of texts."""
        ...

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...
