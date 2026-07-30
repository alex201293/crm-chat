# ADR-002: Estrategia Multi-Tenant con Row-Level Security

**Estado:** Aceptada
**Fecha:** 2024-01-01
**Autor:** Equipo de Arquitectura

## Contexto

La plataforma debe soportar miles de empresas (tenants) con aislamiento total de datos. Necesitamos elegir entre: base de datos por tenant, schema por tenant, o schema compartido con aislamiento por fila.

## Decisión

Adoptar **schema compartido con tenant_id en cada tabla** + PostgreSQL Row-Level Security (RLS) como capa de seguridad adicional.

## Alternativas Consideradas

| Estrategia | Pros | Contras |
|------------|------|---------|
| DB por tenant | Aislamiento perfecto | Inmanejable con miles de tenants, migraciones complejas |
| Schema por tenant | Buen aislamiento, backup individual | Complejidad de connection pooling, migraciones lentas |
| **Schema compartido + RLS** | Simple, escalable, una sola migración | Riesgo de data leak si se olvida filtrar |

## Justificación

- Permite escalar de 1 a 10,000+ tenants sin cambios infraestructurales
- Una sola base de datos = un solo pool de conexiones = menor overhead
- Las migraciones aplican una vez para todos los tenants
- RLS actúa como safety net: aunque la aplicación filtre por tenant_id, PostgreSQL valida a nivel de motor
- Para tenants enterprise con requisitos regulatorios, se puede ofrecer schema dedicado como upgrade

## Implementación

1. Toda tabla incluye `tenant_id UUID NOT NULL`
2. RLS policies aplicadas a tablas de alto volumen
3. Middleware resuelve el tenant del request y lo inyecta en el contexto
4. La sesión de DB setea `app.current_tenant` para las RLS policies
5. Índices compuestos: `(tenant_id, campo_de_búsqueda)`

## Consecuencias

- Cada query debe incluir `tenant_id` en el WHERE (el ORM lo maneja automáticamente)
- Los backups son de toda la DB, no por tenant
- Las queries cross-tenant (analytics globales) requieren un rol sin RLS
- Migraciones destructivas afectan a todos los tenants simultáneamente
