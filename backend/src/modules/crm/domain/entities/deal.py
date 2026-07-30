"""Deal (Opportunity) entity for the CRM module."""

import uuid
from datetime import datetime

from src.modules.crm.domain.events.crm_events import DealStageChanged, DealWon, DealLost
from src.modules.crm.domain.value_objects import DealStatus
from src.shared.domain.base_entity import AggregateRoot


class Deal(AggregateRoot):
    """
    A sales opportunity tracked through pipeline stages.
    Aggregate root that publishes events on stage transitions.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        pipeline_id: uuid.UUID | None = None,
        stage_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        assigned_to_id: uuid.UUID | None = None,
        title: str = "",
        value: int = 0,  # In cents
        currency: str = "USD",
        probability: int = 0,
        expected_close_date: datetime | None = None,
        status: DealStatus = DealStatus.OPEN,
        won_at: datetime | None = None,
        lost_at: datetime | None = None,
        lost_reason: str | None = None,
        tags: list[str] | None = None,
        custom_fields: dict | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.pipeline_id = pipeline_id
        self.stage_id = stage_id
        self.contact_id = contact_id
        self.company_id = company_id
        self.assigned_to_id = assigned_to_id
        self.title = title
        self.value = value
        self.currency = currency
        self.probability = probability
        self.expected_close_date = expected_close_date
        self.status = status
        self.won_at = won_at
        self.lost_at = lost_at
        self.lost_reason = lost_reason
        self.tags = tags or []
        self.custom_fields = custom_fields or {}

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        pipeline_id: uuid.UUID,
        stage_id: uuid.UUID,
        title: str,
        value: int = 0,
        currency: str = "USD",
        contact_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        assigned_to_id: uuid.UUID | None = None,
        expected_close_date: datetime | None = None,
    ) -> "Deal":
        return cls(
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            title=title.strip(),
            value=value,
            currency=currency,
            contact_id=contact_id,
            company_id=company_id,
            assigned_to_id=assigned_to_id,
            expected_close_date=expected_close_date,
            status=DealStatus.OPEN,
        )

    def move_to_stage(self, new_stage_id: uuid.UUID, probability: int | None = None) -> None:
        """Move deal to a new pipeline stage."""
        old_stage_id = self.stage_id
        self.stage_id = new_stage_id
        if probability is not None:
            self.probability = probability
        self.updated_at = datetime.utcnow()

        self.add_domain_event(
            DealStageChanged(
                deal_id=self.id,
                tenant_id=self.tenant_id,
                old_stage_id=old_stage_id,
                new_stage_id=new_stage_id,
            )
        )

    def mark_won(self) -> None:
        """Mark deal as won."""
        self.status = DealStatus.WON
        self.won_at = datetime.utcnow()
        self.probability = 100
        self.updated_at = datetime.utcnow()

        self.add_domain_event(
            DealWon(deal_id=self.id, tenant_id=self.tenant_id, value=self.value)
        )

    def mark_lost(self, reason: str | None = None) -> None:
        """Mark deal as lost."""
        self.status = DealStatus.LOST
        self.lost_at = datetime.utcnow()
        self.lost_reason = reason
        self.probability = 0
        self.updated_at = datetime.utcnow()

        self.add_domain_event(
            DealLost(deal_id=self.id, tenant_id=self.tenant_id, reason=reason)
        )

    def reopen(self) -> None:
        """Reopen a closed deal."""
        self.status = DealStatus.OPEN
        self.won_at = None
        self.lost_at = None
        self.lost_reason = None
        self.updated_at = datetime.utcnow()

    @property
    def value_display(self) -> float:
        return self.value / 100

    @property
    def is_open(self) -> bool:
        return self.status == DealStatus.OPEN
