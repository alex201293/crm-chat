# ADR-007: Stack Frontend - Next.js + Zustand + React Query

**Estado:** Aceptada
**Fecha:** 2024-01-01
**Autor:** Equipo de Arquitectura

## Contexto

El frontend necesita: renderizado rápido, SEO para páginas públicas, estado de servidor con cache inteligente, estado de UI ligero, WebSocket para tiempo real, y un design system consistente.

## Decisión

- **Next.js 14** con App Router para routing y SSR
- **React Query (TanStack)** para estado del servidor (API calls, cache)
- **Zustand** para estado de UI local (chat activo, sidebar, theme)
- **Tailwind CSS** para estilos
- **Zod + react-hook-form** para validación de formularios

## Alternativas Consideradas

### State Management
| Opción | Veredicto |
|--------|-----------|
| Redux Toolkit | Excesivo boilerplate para este caso |
| Jotai | Demasiado atómico, difícil de razonar en stores complejos |
| **Zustand** | Mínimo boilerplate, TypeScript nativo, compatible con SSR |

### Data Fetching
| Opción | Veredicto |
|--------|-----------|
| SWR | Simple pero menos features que React Query |
| **React Query** | Cache, optimistic updates, infinite queries, devtools |
| RTK Query | Atado a Redux |

## Justificación

- React Query maneja el 90% del estado (datos del servidor) con cache automático
- Zustand cubre el 10% restante (estado efímero de UI) sin la ceremonia de Redux
- No hay overlap: React Query = servidor, Zustand = cliente
- Next.js App Router permite streaming SSR y layouts anidados (ideal para dashboard)
- Tailwind + design tokens CSS variables = theming per-tenant sin rebuild

## Consecuencias

- El estado está dividido en dos capas (React Query + Zustand), necesita convención clara
- SSR con Zustand requiere cuidado con hidratación
- Tailwind genera CSS grande en dev (tree-shaked en producción)
- React Query cache puede causar datos stale si el TTL es demasiado largo
