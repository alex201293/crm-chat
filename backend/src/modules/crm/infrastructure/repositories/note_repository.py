"""SQLAlchemy implementation of INoteRepository."""

import uuid

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities.note import Note
from src.modules.crm.domain.interfaces.repositories import INoteRepository
from src.modules.crm.infrastructure.models import NoteModel


class NoteRepository(INoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, note: Note) -> Note:
        model = NoteModel(
            id=note.id,
            tenant_id=note.tenant_id,
            contact_id=note.contact_id,
            deal_id=note.deal_id,
            author_id=note.author_id,
            content=note.content,
            is_pinned=note.is_pinned,
        )
        self._session.add(model)
        await self._session.flush()
        return note

    async def update(self, note: Note) -> Note:
        stmt = select(NoteModel).where(NoteModel.id == note.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Note {note.id} not found")
        model.content = note.content
        model.is_pinned = note.is_pinned
        await self._session.flush()
        return note

    async def delete(
        self, note_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        stmt = sa_delete(NoteModel).where(
            NoteModel.id == note_id,
            NoteModel.tenant_id == tenant_id,
        )
        await self._session.execute(stmt)

    async def list_by_contact(
        self,
        contact_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Note]:
        stmt = (
            select(NoteModel)
            .where(
                NoteModel.contact_id == contact_id,
                NoteModel.tenant_id == tenant_id,
            )
            .order_by(
                NoteModel.is_pinned.desc(),
                NoteModel.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_deal(
        self,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Note]:
        stmt = (
            select(NoteModel)
            .where(
                NoteModel.deal_id == deal_id,
                NoteModel.tenant_id == tenant_id,
            )
            .order_by(
                NoteModel.is_pinned.desc(),
                NoteModel.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: NoteModel) -> Note:
        return Note(
            id=model.id,
            tenant_id=model.tenant_id,
            contact_id=model.contact_id,
            deal_id=model.deal_id,
            author_id=model.author_id,
            content=model.content,
            is_pinned=model.is_pinned,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
