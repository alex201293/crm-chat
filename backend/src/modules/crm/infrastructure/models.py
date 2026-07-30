"""
SQLAlchemy ORM models for the CRM module.
Includes: Contact, Company, Deal, Pipeline, Stage, Task, Note, Activity.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.infrastructure.database.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin


# =============================================================================
# Contact
# =============================================================================
class ContactModel(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """
    A person who interacts with the organization through any channel.
    Links to conversations, deals, and companies.
    """

    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_tenant_email", "tenant_id", "email"),
        Index("ix_contacts_tenant_phone", "tenant_id", "phone"),
        Index("ix_contacts_tenant_name", "tenant_id", "full_name"),
        Index("ix_contacts_external", "tenant_id", "external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )

    # Basic info
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Demographics
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="es")

    # Channel identifiers
    whatsapp_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    telegram_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    facebook_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    instagram_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Segmentation
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Marketing
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    lifecycle_stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="subscriber"
    )  # subscriber, lead, mql, sql, opportunity, customer, evangelist

    # Engagement metrics
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_conversations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Opt-in/consent
    email_opted_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sms_opted_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whatsapp_opted_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    company: Mapped["CompanyModel | None"] = relationship(back_populates="contacts")
    deals: Mapped[list["DealModel"]] = relationship(back_populates="contact")
    notes: Mapped[list["NoteModel"]] = relationship(back_populates="contact")
    activities: Mapped[list["ActivityModel"]] = relationship(back_populates="contact")


# =============================================================================
# Company
# =============================================================================
class CompanyModel(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """A business entity that contacts belong to."""

    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_tenant_name", "tenant_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    annual_revenue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    contacts: Mapped[list["ContactModel"]] = relationship(back_populates="company")


# =============================================================================
# Pipeline
# =============================================================================
class PipelineModel(Base, TimestampMixin, TenantMixin):
    """Sales pipeline with configurable stages."""

    __tablename__ = "pipelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    stages: Mapped[list["PipelineStageModel"]] = relationship(
        back_populates="pipeline", order_by="PipelineStageModel.order"
    )
    deals: Mapped[list["DealModel"]] = relationship(back_populates="pipeline")


# =============================================================================
# Pipeline Stage
# =============================================================================
class PipelineStageModel(Base, TenantMixin):
    """A stage within a pipeline (e.g., New Lead, Contacted, Won)."""

    __tablename__ = "pipeline_stages"
    __table_args__ = (
        Index("ix_pipeline_stages_pipeline_order", "pipeline_id", "order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_won: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    pipeline: Mapped["PipelineModel"] = relationship(back_populates="stages")


# =============================================================================
# Deal (Opportunity)
# =============================================================================
class DealModel(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """
    A sales opportunity tracked through pipeline stages.
    """

    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deals_tenant_stage", "tenant_id", "stage_id"),
        Index("ix_deals_tenant_assigned", "tenant_id", "assigned_to_id"),
        Index("ix_deals_tenant_close_date", "tenant_id", "expected_close_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_stages.id", ondelete="SET NULL"), nullable=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Deal info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # In cents
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_close_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    won_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Custom
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    pipeline: Mapped["PipelineModel"] = relationship(back_populates="deals")
    contact: Mapped["ContactModel | None"] = relationship(back_populates="deals")
    notes: Mapped[list["NoteModel"]] = relationship(back_populates="deal")
    activities: Mapped[list["ActivityModel"]] = relationship(back_populates="deal")


# =============================================================================
# Task
# =============================================================================
class TaskModel(Base, TimestampMixin, TenantMixin):
    """A task related to a contact or deal."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_tenant_assigned_due", "tenant_id", "assigned_to_id", "due_date"),
        Index("ix_tasks_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, in_progress, completed, cancelled
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normal"
    )  # low, normal, high, urgent
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# =============================================================================
# Note
# =============================================================================
class NoteModel(Base, TimestampMixin, TenantMixin):
    """Internal note attached to a contact or deal."""

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    contact: Mapped["ContactModel | None"] = relationship(back_populates="notes")
    deal: Mapped["DealModel | None"] = relationship(back_populates="notes")


# =============================================================================
# Activity (Timeline)
# =============================================================================
class ActivityModel(Base, TenantMixin):
    """
    Timeline activity for contacts and deals.
    Records every significant interaction.
    """

    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_contact_created", "contact_id", "created_at"),
        Index("ix_activities_deal_created", "deal_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    activity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # call, email, meeting, note, deal_stage_changed, message, task_completed
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    contact: Mapped["ContactModel | None"] = relationship(back_populates="activities")
    deal: Mapped["DealModel | None"] = relationship(back_populates="activities")
