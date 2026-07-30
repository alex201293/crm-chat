"""
Base entity and value object definitions for the domain layer.
All domain entities inherit from these base classes.
"""

import uuid
from datetime import datetime


class BaseEntity:
    """
    Base for all domain entities.
    Contains identity and audit fields common to all entities.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class AggregateRoot(BaseEntity):
    """
    Base for aggregate roots.
    Aggregate roots can emit domain events.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._domain_events: list["DomainEvent"] = []

    def add_domain_event(self, event: "DomainEvent") -> None:
        self._domain_events.append(event)

    def clear_domain_events(self) -> list["DomainEvent"]:
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    @property
    def domain_events(self) -> list["DomainEvent"]:
        return self._domain_events.copy()


class DomainEvent:
    """Base domain event."""

    def __init__(self) -> None:
        self.event_id = uuid.uuid4()
        self.occurred_at = datetime.utcnow()
        self.event_type = self.__class__.__name__
