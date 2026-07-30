"""
SQLAlchemy ORM models for the Chat module.
Includes: Conversation, Message, Participant, ConversationAssignment.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.infrastructure.database.base import Base, TenantMixin, TimestampMixin


# =============================================================================
# Conversation
# =============================================================================
class ConversationModel(Base, TimestampMixin, TenantMixin):
    """
    A conversation thread between a contact and the organization.
    Can be handled by AI, a human agent, or both.
    """

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_tenant_status", "tenant_id", "status"),
        Index("ix_conversations_tenant_channel", "tenant_id", "channel"),
        Index("ix_conversations_tenant_assigned", "tenant_id", "assigned_agent_id"),
        Index("ix_conversations_last_message", "tenant_id", "last_message_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    channel: Mapped[str] = mapped_column(
        String(30), nullable=False, default="web"
    )  # web, whatsapp, email, telegram, facebook, instagram
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, pending, resolved, closed
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normal"
    )  # low, normal, high, urgent

    # Assignment
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_ai_handling: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Metadata
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_message_preview: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # SLA tracking
    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # AI confidence tracking
    ai_confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Tags and custom fields
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # Channel-specific external ID (e.g., WhatsApp conversation ID)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    # Relationships
    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="conversation",
        order_by="MessageModel.created_at",
        lazy="dynamic",
    )

    # Satisfaction
    csat_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    csat_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


# =============================================================================
# Message
# =============================================================================
class MessageModel(Base, TenantMixin):
    """
    A single message within a conversation.
    Supports text, images, files, audio, and structured content.
    Partitioned by tenant_id and created_at for performance.
    """

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Sender info
    sender_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, agent, ai, system
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Content
    content_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="text"
    )  # text, image, file, audio, video, location, template, interactive
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Attachments
    attachments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Format: [{"url": "...", "filename": "...", "mime_type": "...", "size": 1234}]

    # Status tracking (for outbound messages)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sent"
    )  # pending, sent, delivered, read, failed

    # AI metadata
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Internal notes (visible only to agents)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Channel-specific message ID
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    # Metadata for channel-specific data (buttons, quick replies, etc.)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    conversation: Mapped["ConversationModel"] = relationship(back_populates="messages")


# =============================================================================
# Conversation Assignment History
# =============================================================================
class ConversationAssignmentModel(Base):
    """
    Tracks the history of conversation assignments (AI → Agent, Agent → Agent).
    Useful for analytics and SLA monitoring.
    """

    __tablename__ = "conversation_assignments"
    __table_args__ = (
        Index("ix_conv_assignments_conversation", "conversation_id", "assigned_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    assignment_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # ai_to_agent, agent_to_agent, manual, auto
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
