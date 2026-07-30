"""SQLAlchemy repositories for the Campaigns module."""

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, DateTime, Boolean, Text, func, select, update
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.campaigns.domain.entities import (
    Campaign,
    CampaignMessage,
    Segment,
)
from src.modules.campaigns.domain.interfaces import (
    ICampaignMessageRepository,
    ICampaignRepository,
    ISegmentRepository,
)
from src.modules.campaigns.domain.value_objects import (
    CampaignChannel,
    CampaignStatus,
    MessageDeliveryStatus,
)
from src.shared.infrastructure.database.base import Base, TenantMixin, TimestampMixin


# =============================================================================
# ORM Models
# =============================================================================
class CampaignModel(Base, TimestampMixin, TenantMixin):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    segment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    template_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    template_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_recipients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    read_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class SegmentModel(Base, TimestampMixin, TenantMixin):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    filters: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    contact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CampaignMessageModel(Base, TenantMixin):
    __tablename__ = "campaign_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# =============================================================================
# Repository Implementations
# =============================================================================
class CampaignRepository(ICampaignRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, campaign: Campaign) -> Campaign:
        model = CampaignModel(
            id=campaign.id, tenant_id=campaign.tenant_id, name=campaign.name,
            channel=campaign.channel.value, status=campaign.status.value,
            segment_id=campaign.segment_id, template_content=campaign.template_content,
            template_name=campaign.template_name, subject=campaign.subject,
            scheduled_at=campaign.scheduled_at, metadata_=campaign.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return campaign

    async def get_by_id(self, campaign_id: uuid.UUID, tenant_id: uuid.UUID) -> Campaign | None:
        stmt = select(CampaignModel).where(
            CampaignModel.id == campaign_id, CampaignModel.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_entity(m) if m else None

    async def update(self, campaign: Campaign) -> Campaign:
        stmt = select(CampaignModel).where(CampaignModel.id == campaign.id)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            raise ValueError(f"Campaign {campaign.id} not found")
        m.name = campaign.name
        m.status = campaign.status.value
        m.scheduled_at = campaign.scheduled_at
        m.started_at = campaign.started_at
        m.completed_at = campaign.completed_at
        m.total_recipients = campaign.total_recipients
        m.sent_count = campaign.sent_count
        m.delivered_count = campaign.delivered_count
        m.read_count = campaign.read_count
        m.clicked_count = campaign.clicked_count
        m.failed_count = campaign.failed_count
        m.conversion_count = campaign.conversion_count
        m.metadata_ = campaign.metadata
        await self._session.flush()
        return campaign

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, status: CampaignStatus | None = None,
        offset: int = 0, limit: int = 20,
    ) -> list[Campaign]:
        stmt = select(CampaignModel).where(CampaignModel.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(CampaignModel.status == status.value)
        stmt = stmt.order_by(CampaignModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count(CampaignModel.id)).where(CampaignModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_scheduled_ready(self) -> list[Campaign]:
        now = datetime.utcnow()
        stmt = select(CampaignModel).where(
            CampaignModel.status == CampaignStatus.SCHEDULED.value,
            CampaignModel.scheduled_at <= now,
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, m: CampaignModel) -> Campaign:
        return Campaign(
            id=m.id, tenant_id=m.tenant_id, name=m.name,
            channel=CampaignChannel(m.channel), status=CampaignStatus(m.status),
            segment_id=m.segment_id, template_content=m.template_content,
            template_name=m.template_name, subject=m.subject,
            scheduled_at=m.scheduled_at, started_at=m.started_at,
            completed_at=m.completed_at, total_recipients=m.total_recipients,
            sent_count=m.sent_count, delivered_count=m.delivered_count,
            read_count=m.read_count, clicked_count=m.clicked_count,
            failed_count=m.failed_count, conversion_count=m.conversion_count,
            metadata=m.metadata_ or {}, created_at=m.created_at, updated_at=m.updated_at,
        )


class SegmentRepository(ISegmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, segment: Segment) -> Segment:
        model = SegmentModel(
            id=segment.id, tenant_id=segment.tenant_id, name=segment.name,
            description=segment.description, filters=segment.filters,
            contact_count=segment.contact_count, is_dynamic=segment.is_dynamic,
        )
        self._session.add(model)
        await self._session.flush()
        return segment

    async def get_by_id(self, segment_id: uuid.UUID, tenant_id: uuid.UUID) -> Segment | None:
        stmt = select(SegmentModel).where(
            SegmentModel.id == segment_id, SegmentModel.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return Segment(
            id=m.id, tenant_id=m.tenant_id, name=m.name, description=m.description,
            filters=m.filters or [], contact_count=m.contact_count,
            is_dynamic=m.is_dynamic, created_at=m.created_at, updated_at=m.updated_at,
        )

    async def update(self, segment: Segment) -> Segment:
        stmt = select(SegmentModel).where(SegmentModel.id == segment.id)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if m:
            m.name = segment.name
            m.description = segment.description
            m.filters = segment.filters
            m.contact_count = segment.contact_count
        await self._session.flush()
        return segment

    async def delete(self, segment_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        from sqlalchemy import delete as sa_delete
        stmt = sa_delete(SegmentModel).where(
            SegmentModel.id == segment_id, SegmentModel.tenant_id == tenant_id
        )
        await self._session.execute(stmt)

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Segment]:
        stmt = select(SegmentModel).where(SegmentModel.tenant_id == tenant_id).order_by(SegmentModel.name)
        result = await self._session.execute(stmt)
        return [
            Segment(id=m.id, tenant_id=m.tenant_id, name=m.name, description=m.description,
                    filters=m.filters or [], contact_count=m.contact_count,
                    is_dynamic=m.is_dynamic, created_at=m.created_at)
            for m in result.scalars().all()
        ]

    async def get_contact_ids(self, segment_id: uuid.UUID, tenant_id: uuid.UUID) -> list[uuid.UUID]:
        """Evaluate segment filters against contacts table."""
        segment = await self.get_by_id(segment_id, tenant_id)
        if not segment:
            return []

        from src.modules.crm.infrastructure.models import ContactModel
        stmt = select(ContactModel.id).where(
            ContactModel.tenant_id == tenant_id,
            ContactModel.deleted_at.is_(None),
        )

        # Apply dynamic filters
        for f in segment.filters:
            field = f.get("field", "")
            operator = f.get("operator", "equals")
            value = f.get("value", "")

            column = getattr(ContactModel, field, None)
            if column is None:
                continue

            if operator == "equals":
                stmt = stmt.where(column == value)
            elif operator == "not_equals":
                stmt = stmt.where(column != value)
            elif operator == "contains":
                stmt = stmt.where(column.ilike(f"%{value}%"))
            elif operator == "exists":
                stmt = stmt.where(column.isnot(None))
            elif operator == "not_exists":
                stmt = stmt.where(column.is_(None))

        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]


class CampaignMessageRepository(ICampaignMessageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, message: CampaignMessage) -> CampaignMessage:
        model = CampaignMessageModel(
            id=message.id, tenant_id=message.tenant_id,
            campaign_id=message.campaign_id, contact_id=message.contact_id,
            status=message.status.value,
        )
        self._session.add(model)
        await self._session.flush()
        return message

    async def create_batch(self, messages: list[CampaignMessage]) -> None:
        models = [
            CampaignMessageModel(
                id=m.id, tenant_id=m.tenant_id,
                campaign_id=m.campaign_id, contact_id=m.contact_id,
                status=m.status.value,
            )
            for m in messages
        ]
        self._session.add_all(models)
        await self._session.flush()

    async def update_status(self, message_id: uuid.UUID, **kwargs) -> None:
        stmt = update(CampaignMessageModel).where(
            CampaignMessageModel.id == message_id
        ).values(**kwargs)
        await self._session.execute(stmt)

    async def get_pending_for_campaign(
        self, campaign_id: uuid.UUID, limit: int = 100
    ) -> list[CampaignMessage]:
        stmt = (
            select(CampaignMessageModel)
            .where(
                CampaignMessageModel.campaign_id == campaign_id,
                CampaignMessageModel.status == MessageDeliveryStatus.PENDING.value,
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            CampaignMessage(
                id=m.id, tenant_id=m.tenant_id, campaign_id=m.campaign_id,
                contact_id=m.contact_id, status=MessageDeliveryStatus(m.status),
                channel_message_id=m.channel_message_id, created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]

    async def count_by_status(self, campaign_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(CampaignMessageModel.status, func.count(CampaignMessageModel.id))
            .where(CampaignMessageModel.campaign_id == campaign_id)
            .group_by(CampaignMessageModel.status)
        )
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
