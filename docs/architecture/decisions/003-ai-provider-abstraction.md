# ADR-003: Capa de Abstracción para Proveedores de IA

**Estado:** Aceptada
**Fecha:** 2024-01-01
**Autor:** Equipo de Arquitectura

## Contexto

El sistema debe soportar múltiples proveedores de IA (OpenAI, Claude, Gemini, Llama, Mistral) y permitir cambiar entre ellos sin modificar la lógica de negocio. Los proveedores tienen APIs diferentes, modelos de pricing distintos, y capabilities variables.

## Decisión

Implementar un **patrón Strategy/Adapter** donde la capa de dominio define una interfaz `ILLMProvider` y cada proveedor implementa un adapter en la capa de infraestructura.

## Diseño

```python
# domain/interfaces/llm_provider.py
class ILLMProvider(Protocol):
    async def complete(self, prompt: str, config: CompletionConfig) -> CompletionResult: ...
    async def stream(self, prompt: str, config: CompletionConfig) -> AsyncIterator[str]: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

# infrastructure/providers/openai_provider.py
class OpenAIProvider(ILLMProvider): ...

# infrastructure/providers/anthropic_provider.py  
class AnthropicProvider(ILLMProvider): ...
```

## Justificación

- El mercado de IA evoluciona rápidamente; necesitamos flexibilidad para adoptar nuevos modelos
- Diferentes tenants pueden preferir diferentes proveedores (por costo, regulación, o rendimiento)
- Permite fallback automático: si OpenAI falla, se puede intentar con Claude
- Facilita A/B testing entre modelos
- El negocio no depende de un solo vendor

## Consecuencias

- Cada nuevo proveedor requiere implementar un adapter (costo bajo)
- Algunas features son provider-specific (function calling, vision) y necesitan graceful degradation
- El prompt engineering puede requerir ajustes por modelo
- Necesitamos normalizar la interfaz de embeddings para que RAG funcione con cualquier proveedor
