"""Domain events for the CRM bounded context."""

import uuid

from src.shared.domain.base_entity import DomainEvent


class ContactCreated(DomainEvent):
    """Emitted when a new contact is created."""

    def __init__(
        self,
        contact_id: uuid.UUID,
        tenant_id: uuid.UUID,
        email: str | None = None,
    ) -> None:
        super().__init__()
        self.contact_id = contact_id
        self.tenant_id = tenant_id
        self.email = email


class DealStageChanged(DomainEvent):
    """Emitted when a deal moves to a different stage."""

    def __init__(
        self,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        old_stage_id: uuid.UUID | None,
        new_stage_id: uuid.UUID,
    ) -> None:
        super().__init__()
        self.deal_id = deal_id
        self.tenant_id = tenant_id
        self.old_stage_id = old_stage_id
        self.new_stage_id = new_stage_id


class DealWon(DomainEvent):
    """Emitted when a deal is marked as won."""

    def __init__(
        self,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        value: int,
    ) -> None:
        super().__init__()
        self.deal_id = deal_id
        self.tenant_id = tenant_id
        self.value = value


class DealLost(DomainEvent):
    """Emitted when a deal is marked as lost."""

    def __init__(
        self,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reason: str | None = None,
    ) -> None:
        super().__init__()
        self.deal_id = deal_id
        self.tenant_id = tenant_id
        self.reason = reason
