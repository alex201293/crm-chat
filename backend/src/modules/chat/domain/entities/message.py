"""
Message entity within a conversation.
Represents a single message sent by a user, agent, AI, or system.
"""

import uuid
from datetime import datetime

from src.modules.chat.domain.value_objects.message_content import (
    Attachment,
    MessageContentType,
    MessageSenderType,
    MessageStatus,
)
from src.shared.domain.base_entity import BaseEntity


class Message(BaseEntity):
    """
    A single message within a conversation.
    Not an aggregate root - managed through the Conversation aggregate.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        sender_type: MessageSenderType = MessageSenderType.USER,
        sender_id: uuid.UUID | None = None,
        sender_name: str = "",
        content_type: MessageContentType = MessageContentType.TEXT,
        content: str = "",
        attachments: list[Attachment] | None = None,
        status: MessageStatus = MessageStatus.SENT,
        ai_generated: bool = False,
        ai_confidence: float | None = None,
        ai_model: str | None = None,
        ai_tokens_used: int | None = None,
        is_internal: bool = False,
        external_id: str | None = None,
        metadata: dict | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.conversation_id = conversation_id
        self.sender_type = sender_type
        self.sender_id = sender_id
        self.sender_name = sender_name
        self.content_type = content_type
        self.content = content
        self.attachments = attachments or []
        self.status = status
        self.ai_generated = ai_generated
        self.ai_confidence = ai_confidence
        self.ai_model = ai_model
        self.ai_tokens_used = ai_tokens_used
        self.is_internal = is_internal
        self.external_id = external_id
        self.metadata = metadata or {}

    @classmethod
    def create_user_message(
        cls,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID | None,
        sender_name: str,
        content: str,
        content_type: MessageContentType = MessageContentType.TEXT,
        attachments: list[Attachment] | None = None,
        channel_message_id: str | None = None,
    ) -> "Message":
        """Factory for creating a user (contact) message."""
        return cls(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            sender_type=MessageSenderType.USER,
            sender_id=sender_id,
            sender_name=sender_name,
            content_type=content_type,
            content=content,
            attachments=attachments,
            external_id=channel_message_id,
        )

    @classmethod
    def create_ai_response(
        cls,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str,
        model: str,
        tokens_used: int,
        confidence: float,
    ) -> "Message":
        """Factory for creating an AI-generated response."""
        return cls(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            sender_type=MessageSenderType.AI,
            sender_name="AI Assistant",
            content_type=MessageContentType.TEXT,
            content=content,
            ai_generated=True,
            ai_model=model,
            ai_tokens_used=tokens_used,
            ai_confidence=confidence,
        )

    @classmethod
    def create_agent_message(
        cls,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        agent_id: uuid.UUID,
        agent_name: str,
        content: str,
        content_type: MessageContentType = MessageContentType.TEXT,
        is_internal: bool = False,
        attachments: list[Attachment] | None = None,
    ) -> "Message":
        """Factory for creating a human agent message."""
        return cls(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            sender_type=MessageSenderType.AGENT,
            sender_id=agent_id,
            sender_name=agent_name,
            content_type=content_type,
            content=content,
            is_internal=is_internal,
            attachments=attachments,
        )

    @classmethod
    def create_system_message(
        cls,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str,
    ) -> "Message":
        """Factory for creating a system notification message."""
        return cls(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            sender_type=MessageSenderType.SYSTEM,
            sender_name="System",
            content_type=MessageContentType.TEXT,
            content=content,
        )

    def mark_delivered(self) -> None:
        self.status = MessageStatus.DELIVERED

    def mark_read(self) -> None:
        self.status = MessageStatus.READ

    def mark_failed(self) -> None:
        self.status = MessageStatus.FAILED

    @property
    def is_from_contact(self) -> bool:
        return self.sender_type == MessageSenderType.USER

    @property
    def is_from_ai(self) -> bool:
        return self.sender_type == MessageSenderType.AI

    @property
    def is_from_agent(self) -> bool:
        return self.sender_type == MessageSenderType.AGENT
