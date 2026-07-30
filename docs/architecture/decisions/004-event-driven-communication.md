# ADR-004: Comunicación Event-Driven entre Módulos

**Estado:** Aceptada
**Fecha:** 2024-01-01
**Autor:** Equipo de Arquitectura

## Contexto

Los módulos necesitan comunicarse entre sí (e.g., cuando un mensaje llega, el CRM actualiza el contacto; cuando una conversación escala, notifica al agente). Necesitamos un mecanismo que mantenga los módulos desacoplados.

## Decisión

Usar **Domain Events** como mecanismo primario de comunicación entre módulos:
- Fase actual: Event bus in-process (patrón Observer)
- Fase futura: RabbitMQ para eventos que requieren durabilidad y procesamiento asíncrono

## Diseño

```
Módulo A publica: ConversationEscalated
   ↓
Event Bus (in-process)
   ↓
Módulo B suscribe: NotificationService.handle_escalation()
Módulo C suscribe: AgentPanel.notify_new_assignment()
```

## Justificación

- Desacopla módulos: el emisor no conoce a los consumidores
- Facilita agregar nuevas reacciones sin modificar el código existente (Open/Closed)
- El event bus in-process es simple y no tiene latencia de red
- Cuando se extraigan microservicios, los eventos se publican en RabbitMQ sin cambiar la interfaz

## Eventos Iniciales del Sistema

| Evento | Publicado por | Consumidores |
|--------|--------------|--------------|
| UserRegistered | Auth | Notifications, CRM |
| MessageReceived | Chat | AI, Knowledge, CRM |
| ConversationEscalated | Chat | Notifications, Agent Panel |
| DealStageChanged | CRM | Activities, Notifications |
| CampaignCompleted | Campaigns | Analytics, Notifications |

## Consecuencias

- Los eventos son fire-and-forget en la fase in-process (no hay retry automático)
- Para operaciones críticas (cobros, envíos), se usará Celery + RabbitMQ con retry y DLQ
- Necesitamos idempotencia en los handlers para la fase distribuida
- El orden de procesamiento no está garantizado entre handlers
