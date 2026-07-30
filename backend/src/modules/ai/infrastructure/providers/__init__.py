"""AI provider adapters. Handles missing SDKs gracefully."""

try:
    from src.modules.ai.infrastructure.providers.openai_provider import OpenAIProvider
except ImportError:
    OpenAIProvider = None  # type: ignore

try:
    from src.modules.ai.infrastructure.providers.anthropic_provider import AnthropicProvider
except ImportError:
    AnthropicProvider = None  # type: ignore

try:
    from src.modules.ai.infrastructure.providers.gemini_provider import GeminiProvider
except ImportError:
    GeminiProvider = None  # type: ignore

try:
    from src.modules.ai.infrastructure.providers.mistral_provider import MistralProvider
except ImportError:
    MistralProvider = None  # type: ignore

__all__ = ["AnthropicProvider", "GeminiProvider", "MistralProvider", "OpenAIProvider"]
