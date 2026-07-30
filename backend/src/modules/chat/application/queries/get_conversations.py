"""
Queries for retrieving conversations and messages.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.modules.chat.domain.interfaces.conversation_repository import (
    IConversationRepository,
    IMessageRepository,
)
from src.modules.chat.domain.value_objects.message_content import ConversationStatus


@dataclass
class ConversationDTO:
    """Conversation data for API responses."""

    id: str
    contact_id: str | None
    channel: str
    status: str
    priority: str
    assigned_agent_id: str | None
    is_ai_handling: bool
    subject: str | None
    last_message_at: str | None
    last_message_preview: str | None
    unread_count: int
    message_count: int
    ai_confidence_score: float | None
    escalation_reason: str | None
    tags: list[str]
    created_at: str


@dataclass
class MessageDTO:
    """Message data for API responses."""

    id: str
    conversation_id: str
    sender_type: str
    sender_id: str | None
    sender_name: str
    content_type: str
    content: str
    attachments: list[dict]
    status: str
    ai_generated: bool
    ai_confidence: float | None
    is_internal: bool
    created_at: str


@dataclass
class ConversationListQuery:
    tenant_id: uuid.UUID
    status: str | None = None
    assigned_to: uuid.UUID | None = None
    is_ai_handling: bool | None = None
    page: int = 1
    page_size: int = 20


@dataclass
class ConversationListResult:
    conversations: list[ConversationDTO]
    total: int
    page: int
    page_size: int


class GetConversationsHandler:
    """Query handler for listing conversations."""

    def __init__(self, conversation_repo: IConversationRepository) -> None:
        self._conversation_repo = conversation_repo

    async def execute(self, query: ConversationListQuery) -> ConversationListResult:
        status = ConversationStatus(query.status) if query.status else None
        offset = (query.page - 1) * query.page_size

        conversations = await self._conversation_repo.list_by_tenant(
            tenant_id=query.tenant_id,
            status=status,
            assigned_to=query.assigned_to,
            is_ai_handling=query.is_ai_handling,
            offset=offset,
            limit=query.page_size,
        )

        total = await self._conversation_repo.count_by_tenant(
            tenant_id=query.tenant_id,
            status=status,
        )

        dtos = [
            ConversationDTO(
                id=str(c.id),
                contact_id=str(c.contact_id) if c.contact_id else None,
                channel=c.channel.value,
                status=c.status.value,
                priority=c.priority.value,
                assigned_agent_id=str(c.assigned_agent_id) if c.assigned_agent_id else None,
                is_ai_handling=c.is_ai_handling,
                subject=c.subject,
                last_message_at=c.last_message_at.isoformat() if c.last_message_at else None,
                last_message_preview=c.last_message_preview,
                unread_count=c.unread_count,
                message_count=c.message_count,
                ai_confidence_score=c.ai_confidence_score,
                escalation_reason=c.escalation_reason,
                tags=c.tags,
                created_at=c.created_at.isoformat() if c.created_at else "",
            )
            for c in conversations
        ]

        return ConversationListResult(
            conversations=dtos,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )


@dataclass
class GetMessagesQuery:
    tenant_id: uuid.UUID
    conversation_id: uuid.UUID
    page: int = 1
    page_size: int = 50


@dataclass
class MessagesListResult:
    messages: list[MessageDTO]
    total: int


class GetMessagesHandler:
    """Query handler for listing messages in a conversation."""

    def __init__(self, message_repo: IMessageRepository) -> None:
        self._message_repo = message_repo

    async def execute(self, query: GetMessagesQuery) -> MessagesListResult:
        offset = (query.page - 1) * query.page_size

        messages = await self._message_repo.get_by_conversation(
            conversation_id=query.conversation_id,
            tenant_id=query.tenant_id,
            offset=offset,
            limit=query.page_size,
        )

        total = await self._message_repo.count_by_conversation(
            conversation_id=query.conversation_id,
            tenant_id=query.tenant_id,
        )

        dtos = [
            MessageDTO(
                id=str(m.id),
                conversation_id=str(m.conversation_id),
                sender_type=m.sender_type.value,
                sender_id=str(m.sender_id) if m.sender_id else None,
                sender_name=m.sender_name,
                content_type=m.content_type.value,
                content=m.content,
                attachments=[a.to_dict() for a in m.attachments],
                status=m.status.value,
                ai_generated=m.ai_generated,
                ai_confidence=m.ai_confidence,
                is_internal=m.is_internal,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in messages
        ]

        return MessagesListResult(messages=dtos, total=total)
