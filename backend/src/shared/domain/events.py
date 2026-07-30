"""
Domain event infrastructure.
Provides an in-process event bus for publishing and subscribing to domain events.
Can be replaced with RabbitMQ publisher when extracting to microservices.
"""

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from src.shared.domain.base_entity import DomainEvent

# Type alias for event handlers
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus:
    """
    In-process async event bus.
    Dispatches domain events to registered handlers.
    Thread-safe for concurrent async access.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type.__name__].append(handler)

    def unsubscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Remove a handler for a specific event type."""
        handlers = self._handlers.get(event_type.__name__, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers."""
        handlers = self._handlers.get(event.event_type, [])
        if handlers:
            await asyncio.gather(
                *(handler(event) for handler in handlers),
                return_exceptions=True,
            )

    async def publish_all(self, events: list[DomainEvent]) -> None:
        """Publish multiple events in order."""
        for event in events:
            await self.publish(event)


# Global event bus instance (singleton within the process)
event_bus = EventBus()
