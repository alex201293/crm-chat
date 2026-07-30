# Arquitectura General - Plataforma SaaS Omnicanal con IA

## 1. Visión General

Plataforma SaaS multi-tenant que combina CRM, chat con IA, automatización y omnicanalidad. Diseñada para escalar a miles de empresas y millones de conversaciones simultáneas.

## 2. Principios Arquitectónicos

| Principio | Aplicación |
|-----------|------------|
| Clean Architecture | Capas independientes: Domain → Application → Infrastructure → API |
| SOLID | Cada módulo tiene responsabilidad única, extensible sin modificar código existente |
| DDD (selectivo) | Bounded Contexts para dominios complejos (Chat, CRM, Campaigns) |
| CQRS (preparado) | Separación lectura/escritura en módulos de alto tráfico |
| Event-Driven | Comunicación asíncrona entre módulos via RabbitMQ |
| Multi-Tenancy | Row-Level Security con tenant_id en toda entidad |

## 3. Bounded Contexts (DDD)

```
┌─────────────────────────────────────────────────────────────────┐
│                        PLATFORM                                  │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────┤
│   Auth   │   Chat   │   CRM    │ Campaign │ Channel  │Knowledge│
│ Context  │ Context  │ Context  │ Context  │ Context  │ Context │
├──────────┼──────────┼──────────┼──────────┼──────────┼─────────┤
│• Users   │• Conver- │• Contacts│• Campaign│• WhatsApp│• Docs   │
│• Roles   │  sations │• Deals   │• Templates• Email   │• Vectors│
│• Tenants │• Messages│• Pipeline│• Segments│• SMS     │• RAG    │
│• Tokens  │• AI Agent│• Tasks   │• Analytics• Telegram│• Index  │
│• MFA     │• Handoff │• Notes   │• Schedule│• Facebook│• FAQ    │
└──────────┴──────────┴──────────┴──────────┴──────────┴─────────┘
```

## 4. Capas de la Arquitectura (por módulo)

```
┌─────────────────────────────────────────┐
│              API Layer                    │  ← FastAPI routers, schemas, middleware
├─────────────────────────────────────────┤
│         Application Layer                │  ← Use cases, DTOs, commands/queries
├─────────────────────────────────────────┤
│           Domain Layer                   │  ← Entities, Value Objects, Domain Events, Interfaces
├─────────────────────────────────────────┤
│        Infrastructure Layer              │  ← Repositories, External APIs, DB, Cache, Queue
└─────────────────────────────────────────┘
```

### Regla de Dependencia
- Domain NO depende de nada externo
- Application depende SOLO de Domain
- Infrastructure implementa interfaces de Domain
- API orquesta Application layer

## 5. Estrategia Multi-Tenant

**Modelo elegido: Schema compartido con Row-Level Security (RLS)**

Justificación:
- Permite escalar a miles de tenants sin overhead de múltiples schemas/DBs
- PostgreSQL RLS garantiza aislamiento a nivel de fila
- Menor complejidad operativa que schema-per-tenant
- Para tenants enterprise (futuro): posibilidad de schema dedicado

```sql
-- Cada tabla incluye tenant_id
-- RLS policy aplicada automáticamente
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON conversations
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

## 6. Comunicación entre Servicios

### Fase actual (monolito modular):
- Comunicación directa entre módulos via interfaces Python
- Eventos internos via patrón Observer/Mediator

### Fase futura (microservicios):
- RabbitMQ para eventos asíncronos (campañas, notificaciones)
- gRPC para comunicación síncrona entre servicios críticos
- Redis Pub/Sub para WebSocket broadcasting

```
┌────────┐     ┌────────────┐     ┌──────────┐
│ API GW │────▶│  Services  │────▶│ RabbitMQ │
└────────┘     └────────────┘     └──────────┘
                     │                   │
                     ▼                   ▼
              ┌────────────┐     ┌──────────────┐
              │ PostgreSQL │     │   Workers    │
              └────────────┘     └──────────────┘
```

## 7. Stack Tecnológico - Justificación

### Backend

| Tecnología | Justificación |
|-----------|---------------|
| **Python 3.13+** | Ecosistema maduro para IA/ML, async nativo, tipado estricto con typing |
| **FastAPI** | Async nativo, validación automática con Pydantic, OpenAPI integrado, alto rendimiento |
| **SQLAlchemy 2.0** | ORM maduro, soporte async, tipado, Unit of Work pattern |
| **Alembic** | Migraciones versionadas, rollback, autogeneración desde modelos |
| **PostgreSQL 16** | JSONB, full-text search, RLS, particionado nativo, extensiones vectoriales (pgvector) |
| **Redis** | Cache, sessions, rate limiting, pub/sub para WebSockets, colas temporales |
| **RabbitMQ** | Message broker robusto, dead letter queues, routing flexible, garantía de entrega |
| **Celery** | Task queue para trabajos pesados (campañas, indexación, procesamiento IA) |
| **pgvector** | Búsqueda vectorial para RAG integrada en PostgreSQL, sin infraestructura adicional |

### Frontend

| Tecnología | Justificación |
|-----------|---------------|
| **Next.js 14+** | SSR/SSG, App Router, API Routes, optimización automática |
| **TypeScript** | Tipado estricto, mejor DX, prevención de errores en compilación |
| **Tailwind CSS** | Utility-first, design system consistente, tree-shaking automático |
| **Zustand** | State management ligero, sin boilerplate, compatible con SSR |
| **React Query** | Cache inteligente, revalidación, optimistic updates, estados de carga |
| **Socket.io Client** | WebSocket con fallback, reconexión automática, rooms |

### Mobile

| Tecnología | Justificación |
|-----------|---------------|
| **Flutter** | Una base de código para iOS/Android, rendimiento nativo, hot reload |
| **Dart** | Tipado fuerte, async/await nativo, compilación AOT |

### Infraestructura

| Tecnología | Justificación |
|-----------|---------------|
| **Docker** | Entornos reproducibles, aislamiento, CI/CD simplificado |
| **Kubernetes** | Orquestación, auto-scaling, rolling deployments, health checks |
| **Nginx** | Reverse proxy, SSL termination, rate limiting a nivel de red |
| **GitHub Actions** | CI/CD integrado, workflows declarativos |

## 8. Seguridad

- **Autenticación**: JWT (access 15min) + Refresh Token (7 días, rotación)
- **Autorización**: RBAC con permisos granulares por recurso
- **Multi-factor**: TOTP (Google Authenticator) + SMS fallback
- **Rate Limiting**: Por IP, por usuario, por tenant (Redis-backed)
- **Auditoría**: Log de toda acción sensible con actor, timestamp, IP
- **Encriptación**: TLS 1.3 en tránsito, AES-256 para datos sensibles at rest
- **Input Validation**: Pydantic schemas en toda entrada
- **CORS**: Whitelist por tenant
- **Headers**: HSTS, X-Frame-Options, CSP, X-Content-Type-Options

## 9. Estrategia de Escalabilidad

### Horizontal
- Stateless services → múltiples réplicas detrás de load balancer
- WebSocket sticky sessions via Redis adapter
- Read replicas de PostgreSQL para queries pesadas

### Vertical (datos)
- Particionado por tenant_id en tablas de alto volumen (messages, events)
- Índices parciales y compuestos
- Archivado automático de conversaciones antiguas

### Caché
- L1: In-process (per-request)
- L2: Redis (shared, TTL-based)
- Invalidación por eventos

## 10. Preparación para Microservicios

El monolito modular está diseñado para extraer servicios sin reescribir:

```
Módulo actual          →  Servicio futuro
─────────────────────────────────────────
auth/                  →  auth-service
chat/                  →  chat-service (+ WebSocket service)
crm/                   →  crm-service
campaigns/             →  campaign-service
channels/whatsapp/     →  whatsapp-service
channels/email/        →  email-service
knowledge/             →  knowledge-service (RAG)
ai/                    →  ai-gateway-service
billing/               →  billing-service
notifications/         →  notification-service
```

Cada módulo ya expone interfaces (ports) que pueden convertirse en contratos gRPC/REST.

## 11. Diagrama de Despliegue

```
                    ┌─────────────┐
                    │   CDN/WAF   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Nginx     │
                    │  (Ingress)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌─────▼─────┐
       │  Frontend   │ │  API │ │ WebSocket  │
       │  (Next.js)  │ │ (GW) │ │  Server    │
       └─────────────┘ └──┬───┘ └─────┬─────┘
                           │           │
                    ┌──────▼───────────▼──────┐
                    │     Backend Services     │
                    │      (FastAPI pods)      │
                    └──────┬──────────┬───────┘
                           │          │
              ┌────────────┼──────────┼────────────┐
              │            │          │            │
       ┌──────▼──┐  ┌─────▼──┐ ┌────▼───┐ ┌─────▼────┐
       │PostgreSQL│  │ Redis  │ │RabbitMQ│ │  Celery  │
       │ + pgvec │  │Cluster │ │Cluster │ │ Workers  │
       └─────────┘  └────────┘ └────────┘ └──────────┘
```

## 12. Monitoreo y Observabilidad

- **Logs**: Structured logging (JSON) → ELK/Loki
- **Métricas**: Prometheus + Grafana
- **Tracing**: OpenTelemetry → Jaeger
- **Alertas**: Grafana Alerting / PagerDuty
- **Health Checks**: /health, /ready en cada servicio
