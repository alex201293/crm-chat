# ADR-001: Monolito Modular como Arquitectura Inicial

**Estado:** Aceptada
**Fecha:** 2024-01-01
**Autor:** Equipo de Arquitectura

## Contexto

Necesitamos definir la arquitectura inicial para una plataforma SaaS que integra CRM, Chat con IA, campañas y omnicanalidad. El sistema debe escalar a miles de tenants y millones de conversaciones.

## Decisión

Adoptar un **monolito modular** con bounded contexts bien definidos, preparado para extraer microservicios cuando la escala lo justifique.

## Alternativas Consideradas

| Alternativa | Pros | Contras |
|-------------|------|---------|
| Microservicios desde inicio | Escalabilidad independiente, equipos autónomos | Complejidad operacional prematura, overhead de red, debugging difícil |
| Monolito tradicional | Simple de desarrollar | Acoplamiento, difícil de escalar selectivamente |
| **Monolito modular** | Velocidad de desarrollo + preparado para escalar | Requiere disciplina en boundaries |

## Justificación

- Fase temprana del producto: velocidad de iteración es más valiosa que escalabilidad extrema
- Un equipo pequeño no necesita la coordinación que imponen los microservicios
- Los módulos ya respetan contratos (interfaces) que facilitan la extracción futura
- Comunicación intra-proceso es más rápida y simple de debuggear
- PostgreSQL con RLS escala verticalmente hasta millones de filas por tabla

## Consecuencias

- Los módulos se comunican via interfaces Python, no via red
- El deploy es una sola unidad (un container backend)
- La extracción a microservicios requiere: implementar interfaces como gRPC/REST, separar DB schemas, configurar message broker
- Se necesita disciplina para no crear dependencias circulares entre módulos
