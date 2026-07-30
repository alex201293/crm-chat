"""Domain entities for the Campaigns module."""

import uuid
from datetime import datetime

from src.modules.campaigns.domain.value_objects import (
    CampaignChannel,
    CampaignStatus,
    MessageDeliveryStatus,
    SegmentOperator,
)
from src.shared.domain.base_entity import AggregateRoot, BaseEntity


class Campaign(AggregateRoot):
    """
    A marketing/communication campaign sent to a segment of contacts.
    Tracks sending progress and engagement metrics.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        name: str = "",
        channel: CampaignChannel = CampaignChannel.WHATSAPP,
        status: CampaignStatus = CampaignStatus.DRAFT,
        segment_id: uuid.UUID | None = None,
        template_content: str = "",
        template_name: str | None = None,
        subject: str | None = None,  # For email
        scheduled_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        # Metrics
        total_recipients: int = 0,
        sent_count: int = 0,
        delivered_count: int = 0,
        read_count: int = 0,
        clicked_count: int = 0,
        failed_count: int = 0,
        conversion_count: int = 0,
        # Settings
        metadata: dict | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.name = name
        self.channel = channel
        self.status = status
        self.segment_id = segment_id
        self.template_content = template_content
        self.template_name = template_name
        self.subject = subject
        self.scheduled_at = scheduled_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.total_recipients = total_recipients
        self.sent_count = sent_count
        self.delivered_count = delivered_count
        self.read_count = read_count
        self.clicked_count = clicked_count
        self.failed_count = failed_count
        self.conversion_count = conversion_count
        self.metadata = metadata or {}

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        name: str,
        channel: CampaignChannel,
        template_content: str,
        segment_id: uuid.UUID | None = None,
        template_name: str | None = None,
        subject: str | None = None,
    ) -> "Campaign":
        return cls(
            tenant_id=tenant_id,
            name=name.strip(),
            channel=channel,
            template_content=template_content,
            segment_id=segment_id,
            template_name=template_name,
            subject=subject,
            status=CampaignStatus.DRAFT,
        )

    def schedule(self, send_at: datetime) -> None:
        self.scheduled_at = send_at
        self.status = CampaignStatus.SCHEDULED
        self.updated_at = datetime.utcnow()

    def start_sending(self, total_recipients: int) -> None:
        self.status = CampaignStatus.SENDING
        self.started_at = datetime.utcnow()
        self.total_recipients = total_recipients
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        self.status = CampaignStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def pause(self) -> None:
        self.status = CampaignStatus.PAUSED
        self.updated_at = datetime.utcnow()

    def resume(self) -> None:
        self.status = CampaignStatus.SENDING
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        self.status = CampaignStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def increment_sent(self) -> None:
        self.sent_count += 1

    def increment_delivered(self) -> None:
        self.delivered_count += 1

    def increment_read(self) -> None:
        self.read_count += 1

    def increment_clicked(self) -> None:
        self.clicked_count += 1

    def increment_failed(self) -> None:
        self.failed_count += 1

    @property
    def delivery_rate(self) -> float:
        if self.sent_count == 0:
            return 0.0
        return self.delivered_count / self.sent_count

    @property
    def open_rate(self) -> float:
        if self.delivered_count == 0:
            return 0.0
        return self.read_count / self.delivered_count

    @property
    def click_rate(self) -> float:
        if self.delivered_count == 0:
            return 0.0
        return self.clicked_count / self.delivered_count

    @property
    def is_sendable(self) -> bool:
        return self.status in (CampaignStatus.DRAFT, CampaignStatus.SCHEDULED)


class Segment(BaseEntity):
    """
    A segment defines a group of contacts targeted by a campaign.
    Uses filter conditions to dynamically select contacts.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        name: str = "",
        description: str | None = None,
        filters: list[dict] | None = None,
        # filters: [{"field": "lifecycle_stage", "operator": "equals", "value": "customer"}]
        contact_count: int = 0,
        is_dynamic: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.name = name
        self.description = description
        self.filters = filters or []
        self.contact_count = contact_count
        self.is_dynamic = is_dynamic
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        name: str,
        filters: list[dict],
        description: str | None = None,
    ) -> "Segment":
        return cls(
            tenant_id=tenant_id,
            name=name.strip(),
            description=description,
            filters=filters,
            is_dynamic=True,
        )


class CampaignMessage(BaseEntity):
    """
    Tracks individual message delivery within a campaign.
    One record per contact per campaign.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        channel_message_id: str | None = None,
        status: MessageDeliveryStatus = MessageDeliveryStatus.PENDING,
        sent_at: datetime | None = None,
        delivered_at: datetime | None = None,
        read_at: datetime | None = None,
        clicked_at: datetime | None = None,
        failed_at: datetime | None = None,
        error_message: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.campaign_id = campaign_id
        self.contact_id = contact_id
        self.channel_message_id = channel_message_id
        self.status = status
        self.sent_at = sent_at
        self.delivered_at = delivered_at
        self.read_at = read_at
        self.clicked_at = clicked_at
        self.failed_at = failed_at
        self.error_message = error_message

    def mark_sent(self, channel_message_id: str) -> None:
        self.status = MessageDeliveryStatus.SENT
        self.channel_message_id = channel_message_id
        self.sent_at = datetime.utcnow()

    def mark_delivered(self) -> None:
        self.status = MessageDeliveryStatus.DELIVERED
        self.delivered_at = datetime.utcnow()

    def mark_read(self) -> None:
        self.status = MessageDeliveryStatus.READ
        self.read_at = datetime.utcnow()

    def mark_clicked(self) -> None:
        self.status = MessageDeliveryStatus.CLICKED
        self.clicked_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = MessageDeliveryStatus.FAILED
        self.failed_at = datetime.utcnow()
        self.error_message = error
