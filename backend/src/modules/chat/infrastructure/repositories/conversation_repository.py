"""SQLAlchemy implementation of IConversationRepository."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.chat.domain.entities.conversation import Conversation
from src.modules.chat.domain.interfaces.conversation_repository import IConversationRepository
from src.modules.chat.domain.value_objects.message_content import (
    Channel,
    ConversationPriority,
    ConversationStatus,
)
from src.modules.chat.infrastructure.models import ConversationModel


class ConversationRepository(IConversationRepository):
    """PostgreSQL conversation repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation: Conversation) -> Conversation:
        model = ConversationModel(
            id=conversation.id,
            tenant_id=conversation.tenant_id,
            contact_id=conversation.contact_id,
            channel=conversation.channel.value,
            status=conversation.status.value,
            priority=conversation.priority.value,
            assigned_agent_id=conversation.assigned_agent_id,
            is_ai_handling=conversation.is_ai_handling,
            subject=conversation.subject,
            last_message_at=conversation.last_message_at,
            last_message_preview=conversation.last_message_preview,
            unread_count=conversation.unread_count,
            message_count=conversation.message_count,
            first_response_at=conversation.first_response_at,
            resolved_at=conversation.resolved_at,
            ai_confidence_score=conversation.ai_confidence_score,
            escalation_reason=conversation.escalation_reason,
            tags=conversation.tags,
            metadata_=conversation.metadata,
            external_id=conversation.external_id,
            csat_score=conversation.csat_score,
        )
        self._session.add(model)
        await self._session.flush()
        return conversation

    async def get_by_id(
        self, conversation_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Conversation | None:
        stmt = select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_external_id(
        self, external_id: str, tenant_id: uuid.UUID
    ) -> Conversation | None:
        stmt = select(ConversationModel).where(
            ConversationModel.external_id == external_id,
            ConversationModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def update(self, conversation: Conversation) -> Conversation:
        stmt = select(ConversationModel).where(ConversationModel.id == conversation.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Conversation {conversation.id} not found")

        model.status = conversation.status.value
        model.priority = conversation.priority.value
        model.assigned_agent_id = conversation.assigned_agent_id
        model.is_ai_handling = conversation.is_ai_handling
        model.subject = conversation.subject
        model.last_message_at = conversation.last_message_at
        model.last_message_preview = conversation.last_message_preview
        model.unread_count = conversation.unread_count
        model.message_count = conversation.message_count
        model.first_response_at = conversation.first_response_at
        model.resolved_at = conversation.resolved_at
        model.ai_confidence_score = conversation.ai_confidence_score
        model.escalation_reason = conversation.escalation_reason
        model.tags = conversation.tags
        model.metadata_ = conversation.metadata
        model.csat_score = conversation.csat_score

        await self._session.flush()
        return conversation

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: ConversationStatus | None = None,
        assigned_to: uuid.UUID | None = None,
        is_ai_handling: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Conversation]:
        stmt = select(ConversationModel).where(
            ConversationModel.tenant_id == tenant_id
        )

        if status:
            stmt = stmt.where(ConversationModel.status == status.value)
        if assigned_to is not None:
            stmt = stmt.where(ConversationModel.assigned_agent_id == assigned_to)
        if is_ai_handling is not None:
            stmt = stmt.where(ConversationModel.is_ai_handling == is_ai_handling)

        stmt = (
            stmt.order_by(ConversationModel.last_message_at.desc().nullslast())
            .offset(offset)
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def count_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: ConversationStatus | None = None,
    ) -> int:
        stmt = select(func.count(ConversationModel.id)).where(
            ConversationModel.tenant_id == tenant_id
        )
        if status:
            stmt = stmt.where(ConversationModel.status == status.value)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_pending_for_assignment(
        self, tenant_id: uuid.UUID, limit: int = 10
    ) -> list[Conversation]:
        stmt = (
            select(ConversationModel)
            .where(
                ConversationModel.tenant_id == tenant_id,
                ConversationModel.status == ConversationStatus.PENDING.value,
                ConversationModel.assigned_agent_id.is_(None),
            )
            .order_by(
                ConversationModel.priority.desc(),
                ConversationModel.last_message_at.asc(),
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            tenant_id=model.tenant_id,
            contact_id=model.contact_id,
            channel=Channel(model.channel),
            status=ConversationStatus(model.status),
            priority=ConversationPriority(model.priority),
            assigned_agent_id=model.assigned_agent_id,
            is_ai_handling=model.is_ai_handling,
            subject=model.subject,
            last_message_at=model.last_message_at,
            last_message_preview=model.last_message_preview,
            unread_count=model.unread_count,
            message_count=model.message_count,
            first_response_at=model.first_response_at,
            resolved_at=model.resolved_at,
            ai_confidence_score=model.ai_confidence_score,
            escalation_reason=model.escalation_reason,
            tags=model.tags or [],
            metadata=model.metadata_ or {},
            external_id=model.external_id,
            csat_score=model.csat_score,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
