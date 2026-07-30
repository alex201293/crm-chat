"""
Conversation aggregate root.
Manages the lifecycle of a conversation between a contact and the organization.
"""

import uuid
from datetime import datetime

from src.modules.chat.domain.events.chat_events import (
    ConversationClosed,
    ConversationCreated,
    ConversationEscalated,
    ConversationResolved,
)
from src.modules.chat.domain.value_objects.message_content import (
    Channel,
    ConversationPriority,
    ConversationStatus,
    EscalationReason,
)
from src.shared.domain.base_entity import AggregateRoot


class Conversation(AggregateRoot):
    """
    Conversation aggregate root.
    A conversation is a thread of messages between a contact and the organization,
    handled by AI, a human agent, or both.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        channel: Channel = Channel.WEB,
        status: ConversationStatus = ConversationStatus.ACTIVE,
        priority: ConversationPriority = ConversationPriority.NORMAL,
        assigned_agent_id: uuid.UUID | None = None,
        is_ai_handling: bool = True,
        subject: str | None = None,
        last_message_at: datetime | None = None,
        last_message_preview: str | None = None,
        unread_count: int = 0,
        message_count: int = 0,
        first_response_at: datetime | None = None,
        resolved_at: datetime | None = None,
        ai_confidence_score: float | None = None,
        escalation_reason: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        external_id: str | None = None,
        csat_score: int | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.contact_id = contact_id
        self.channel = channel
        self.status = status
        self.priority = priority
        self.assigned_agent_id = assigned_agent_id
        self.is_ai_handling = is_ai_handling
        self.subject = subject
        self.last_message_at = last_message_at
        self.last_message_preview = last_message_preview
        self.unread_count = unread_count
        self.message_count = message_count
        self.first_response_at = first_response_at
        self.resolved_at = resolved_at
        self.ai_confidence_score = ai_confidence_score
        self.escalation_reason = escalation_reason
        self.tags = tags or []
        self.metadata = metadata or {}
        self.external_id = external_id
        self.csat_score = csat_score

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        contact_id: uuid.UUID | None,
        channel: Channel = Channel.WEB,
        subject: str | None = None,
        external_id: str | None = None,
        metadata: dict | None = None,
    ) -> "Conversation":
        """Factory for creating a new conversation."""
        conversation = cls(
            tenant_id=tenant_id,
            contact_id=contact_id,
            channel=channel,
            subject=subject,
            external_id=external_id,
            metadata=metadata,
            is_ai_handling=True,
            status=ConversationStatus.ACTIVE,
        )
        conversation.add_domain_event(
            ConversationCreated(
                conversation_id=conversation.id,
                tenant_id=tenant_id,
                channel=channel.value,
                contact_id=contact_id,
            )
        )
        return conversation

    def record_message(self, preview: str, is_from_agent: bool = False) -> None:
        """Update conversation metadata after a new message."""
        self.last_message_at = datetime.utcnow()
        self.last_message_preview = preview[:200] if preview else None
        self.message_count += 1

        if not is_from_agent:
            self.unread_count += 1

        # Record first response time
        if is_from_agent and not self.first_response_at and self.message_count > 1:
            self.first_response_at = datetime.utcnow()

    def mark_read(self) -> None:
        """Mark all messages as read (agent viewed the conversation)."""
        self.unread_count = 0

    def escalate_to_human(self, reason: EscalationReason) -> None:
        """
        Transfer conversation from AI to human agent queue.
        Sets status to pending and records the reason.
        """
        self.is_ai_handling = False
        self.status = ConversationStatus.PENDING
        self.escalation_reason = reason.description
        self.ai_confidence_score = reason.ai_confidence
        self.priority = ConversationPriority.HIGH
        self.updated_at = datetime.utcnow()

        self.add_domain_event(
            ConversationEscalated(
                conversation_id=self.id,
                tenant_id=self.tenant_id,
                reason=reason.description,
                reason_type=reason.reason_type,
            )
        )

    def assign_agent(self, agent_id: uuid.UUID) -> None:
        """Assign a human agent to this conversation."""
        self.assigned_agent_id = agent_id
        self.is_ai_handling = False
        self.status = ConversationStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def resolve(self) -> None:
        """Mark conversation as resolved."""
        self.status = ConversationStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        self.add_domain_event(
            ConversationResolved(
                conversation_id=self.id,
                tenant_id=self.tenant_id,
            )
        )

    def close(self) -> None:
        """Permanently close the conversation."""
        self.status = ConversationStatus.CLOSED
        self.updated_at = datetime.utcnow()

        self.add_domain_event(
            ConversationClosed(
                conversation_id=self.id,
                tenant_id=self.tenant_id,
            )
        )

    def reopen(self) -> None:
        """Reopen a resolved/closed conversation."""
        self.status = ConversationStatus.ACTIVE
        self.resolved_at = None
        self.updated_at = datetime.utcnow()

    def update_ai_confidence(self, score: float) -> None:
        """Update the AI confidence score for this conversation."""
        self.ai_confidence_score = score

    @property
    def is_assigned(self) -> bool:
        return self.assigned_agent_id is not None

    @property
    def is_open(self) -> bool:
        return self.status in (ConversationStatus.ACTIVE, ConversationStatus.PENDING)
