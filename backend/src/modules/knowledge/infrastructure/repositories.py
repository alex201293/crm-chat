"""SQLAlchemy repository implementations for the Knowledge module."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.knowledge.domain.entities.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    FAQ,
)
from src.modules.knowledge.domain.interfaces.repositories import (
    IChunkRepository,
    IDocumentRepository,
    IFAQRepository,
)
from src.modules.knowledge.infrastructure.vectorstore.models import (
    DocumentModel,
    FAQModel,
)
from src.modules.knowledge.infrastructure.vectorstore.pgvector_store import (
    DocumentChunkModel,
)


class DocumentRepository(IDocumentRepository):
    """PostgreSQL document repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            id=document.id,
            tenant_id=document.tenant_id,
            title=document.title,
            document_type=document.document_type.value,
            source_url=document.source_url,
            file_path=document.file_path,
            file_size=document.file_size,
            mime_type=document.mime_type,
            status=document.status.value,
            chunk_count=document.chunk_count,
            character_count=document.character_count,
            error_message=document.error_message,
            metadata_=document.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return document

    async def get_by_id(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> Document | None:
        stmt = select(DocumentModel).where(
            DocumentModel.id == doc_id,
            DocumentModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, document: Document) -> Document:
        stmt = select(DocumentModel).where(DocumentModel.id == document.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Document {document.id} not found")

        model.title = document.title
        model.status = document.status.value
        model.chunk_count = document.chunk_count
        model.character_count = document.character_count
        model.error_message = document.error_message
        model.metadata_ = document.metadata
        await self._session.flush()
        return document

    async def delete(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        stmt = delete(DocumentModel).where(
            DocumentModel.id == doc_id, DocumentModel.tenant_id == tenant_id
        )
        await self._session.execute(stmt)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: DocumentStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Document]:
        stmt = select(DocumentModel).where(DocumentModel.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(DocumentModel.status == status.value)
        stmt = stmt.order_by(DocumentModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count(DocumentModel.id)).where(
            DocumentModel.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _to_entity(self, model: DocumentModel) -> Document:
        return Document(
            id=model.id,
            tenant_id=model.tenant_id,
            title=model.title,
            document_type=DocumentType(model.document_type),
            source_url=model.source_url,
            file_path=model.file_path,
            file_size=model.file_size,
            mime_type=model.mime_type,
            status=DocumentStatus(model.status),
            chunk_count=model.chunk_count,
            character_count=model.character_count,
            error_message=model.error_message,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class FAQRepository(IFAQRepository):
    """PostgreSQL FAQ repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, faq: FAQ) -> FAQ:
        model = FAQModel(
            id=faq.id,
            tenant_id=faq.tenant_id,
            document_id=faq.document_id,
            question=faq.question,
            answer=faq.answer,
            category=faq.category,
            order=faq.order,
            is_active=faq.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        return faq

    async def update(self, faq: FAQ) -> FAQ:
        stmt = select(FAQModel).where(FAQModel.id == faq.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"FAQ {faq.id} not found")
        model.question = faq.question
        model.answer = faq.answer
        model.category = faq.category
        model.order = faq.order
        model.is_active = faq.is_active
        await self._session.flush()
        return faq

    async def delete(self, faq_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        stmt = delete(FAQModel).where(FAQModel.id == faq_id, FAQModel.tenant_id == tenant_id)
        await self._session.execute(stmt)

    async def list_by_tenant(self, tenant_id: uuid.UUID, category: str | None = None) -> list[FAQ]:
        stmt = select(FAQModel).where(FAQModel.tenant_id == tenant_id, FAQModel.is_active.is_(True))
        if category:
            stmt = stmt.where(FAQModel.category == category)
        stmt = stmt.order_by(FAQModel.order)
        result = await self._session.execute(stmt)
        return [
            FAQ(
                id=m.id, tenant_id=m.tenant_id, document_id=m.document_id,
                question=m.question, answer=m.answer, category=m.category,
                order=m.order, is_active=m.is_active, created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]
