"""SQLAlchemy implementation of IMessageRepository."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.chat.domain.entities.message import Message
from src.modules.chat.domain.interfaces.conversation_repository import IMessageRepository
from src.modules.chat.domain.value_objects.message_content import (
    Attachment,
    MessageContentType,
    MessageSenderType,
    MessageStatus,
)
from src.modules.chat.infrastructure.models import MessageModel


class MessageRepository(IMessageRepository):
    """PostgreSQL message repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, message: Message) -> Message:
        attachments_data = [a.to_dict() for a in message.attachments] if message.attachments else []

        model = MessageModel(
            id=message.id,
            tenant_id=message.tenant_id,
            conversation_id=message.conversation_id,
            sender_type=message.sender_type.value,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            content_type=message.content_type.value,
            content=message.content,
            attachments=attachments_data,
            status=message.status.value,
            ai_generated=message.ai_generated,
            ai_confidence=message.ai_confidence,
            ai_model=message.ai_model,
            ai_tokens_used=message.ai_tokens_used,
            is_internal=message.is_internal,
            external_id=message.external_id,
            metadata_=message.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return message

    async def get_by_conversation(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[Message]:
        stmt = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id,
            MessageModel.tenant_id == tenant_id,
        )

        if before:
            stmt = stmt.where(MessageModel.created_at < before)

        stmt = (
            stmt.order_by(MessageModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        # Return in chronological order (oldest first)
        return [self._to_entity(m) for m in reversed(list(models))]

    async def get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        """Get conversation history formatted for AI context."""
        stmt = (
            select(MessageModel)
            .where(
                MessageModel.conversation_id == conversation_id,
                MessageModel.tenant_id == tenant_id,
                MessageModel.is_internal.is_(False),
            )
            .order_by(MessageModel.created_at.desc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        models = list(reversed(list(result.scalars().all())))

        history: list[dict[str, str]] = []
        for model in models:
            if model.sender_type in (
                MessageSenderType.USER.value,
            ):
                history.append({"role": "user", "content": model.content})
            elif model.sender_type in (
                MessageSenderType.AI.value,
                MessageSenderType.AGENT.value,
            ):
                history.append({"role": "assistant", "content": model.content})

        return history

    async def count_by_conversation(
        self, conversation_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        stmt = select(func.count(MessageModel.id)).where(
            MessageModel.conversation_id == conversation_id,
            MessageModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _to_entity(self, model: MessageModel) -> Message:
        attachments = []
        if model.attachments:
            for att_data in model.attachments:
                attachments.append(
                    Attachment(
                        url=att_data.get("url", ""),
                        filename=att_data.get("filename", ""),
                        mime_type=att_data.get("mime_type", ""),
                        size_bytes=att_data.get("size", 0),
                    )
                )

        return Message(
            id=model.id,
            tenant_id=model.tenant_id,
            conversation_id=model.conversation_id,
            sender_type=MessageSenderType(model.sender_type),
            sender_id=model.sender_id,
            sender_name=model.sender_name,
            content_type=MessageContentType(model.content_type),
            content=model.content,
            attachments=attachments,
            status=MessageStatus(model.status),
            ai_generated=model.ai_generated,
            ai_confidence=model.ai_confidence,
            ai_model=model.ai_model,
            ai_tokens_used=model.ai_tokens_used,
            is_internal=model.is_internal,
            external_id=model.external_id,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
        )
