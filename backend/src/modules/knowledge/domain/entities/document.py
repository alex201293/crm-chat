"""
Document and DocumentChunk entities for the Knowledge Base.
"""

import uuid
from datetime import datetime
from enum import Enum

from src.shared.domain.base_entity import AggregateRoot, BaseEntity


class DocumentStatus(str, Enum):
    """Document processing lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    HTML = "html"
    URL = "url"
    FAQ = "faq"


class Document(AggregateRoot):
    """
    A knowledge base document uploaded by a tenant.
    Contains metadata about the source and processing state.
    Chunks are created during indexing.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        title: str = "",
        document_type: DocumentType = DocumentType.TXT,
        source_url: str | None = None,
        file_path: str | None = None,
        file_size: int = 0,
        mime_type: str | None = None,
        status: DocumentStatus = DocumentStatus.PENDING,
        chunk_count: int = 0,
        character_count: int = 0,
        error_message: str | None = None,
        metadata: dict | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.title = title
        self.document_type = document_type
        self.source_url = source_url
        self.file_path = file_path
        self.file_size = file_size
        self.mime_type = mime_type
        self.status = status
        self.chunk_count = chunk_count
        self.character_count = character_count
        self.error_message = error_message
        self.metadata = metadata or {}

    @classmethod
    def create_from_file(
        cls,
        tenant_id: uuid.UUID,
        title: str,
        document_type: DocumentType,
        file_path: str,
        file_size: int,
        mime_type: str,
    ) -> "Document":
        return cls(
            tenant_id=tenant_id,
            title=title,
            document_type=document_type,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            status=DocumentStatus.PENDING,
        )

    @classmethod
    def create_from_url(
        cls,
        tenant_id: uuid.UUID,
        title: str,
        source_url: str,
    ) -> "Document":
        return cls(
            tenant_id=tenant_id,
            title=title,
            document_type=DocumentType.URL,
            source_url=source_url,
            status=DocumentStatus.PENDING,
        )

    @classmethod
    def create_faq(
        cls,
        tenant_id: uuid.UUID,
        title: str,
    ) -> "Document":
        return cls(
            tenant_id=tenant_id,
            title=title,
            document_type=DocumentType.FAQ,
            status=DocumentStatus.INDEXED,
        )

    def mark_processing(self) -> None:
        self.status = DocumentStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_indexed(self, chunk_count: int, character_count: int) -> None:
        self.status = DocumentStatus.INDEXED
        self.chunk_count = chunk_count
        self.character_count = character_count
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = DocumentStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.utcnow()


class DocumentChunk(BaseEntity):
    """
    A chunk of text from a document, with its vector embedding.
    Used for semantic search (RAG).
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        content: str = "",
        embedding: list[float] | None = None,
        chunk_index: int = 0,
        token_count: int = 0,
        metadata: dict | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.document_id = document_id
        self.content = content
        self.embedding = embedding
        self.chunk_index = chunk_index
        self.token_count = token_count
        self.metadata = metadata or {}

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        content: str,
        chunk_index: int,
        token_count: int,
        metadata: dict | None = None,
    ) -> "DocumentChunk":
        return cls(
            tenant_id=tenant_id,
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            token_count=token_count,
            metadata=metadata,
        )


class FAQ(BaseEntity):
    """A frequently asked question with a pre-defined answer."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        question: str = "",
        answer: str = "",
        category: str | None = None,
        order: int = 0,
        is_active: bool = True,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.document_id = document_id
        self.question = question
        self.answer = answer
        self.category = category
        self.order = order
        self.is_active = is_active
