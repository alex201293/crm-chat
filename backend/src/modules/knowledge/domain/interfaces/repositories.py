"""Repository and service interfaces for the Knowledge module."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.modules.knowledge.domain.entities.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    FAQ,
)


class IDocumentRepository(ABC):
    """Port for document persistence."""

    @abstractmethod
    async def create(self, document: Document) -> Document: ...

    @abstractmethod
    async def get_by_id(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> Document | None: ...

    @abstractmethod
    async def update(self, document: Document) -> Document: ...

    @abstractmethod
    async def delete(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: DocumentStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Document]: ...

    @abstractmethod
    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int: ...


class IChunkRepository(ABC):
    """Port for document chunk persistence."""

    @abstractmethod
    async def create_many(self, chunks: list[DocumentChunk]) -> None: ...

    @abstractmethod
    async def delete_by_document(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def get_by_document(
        self, document_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[DocumentChunk]: ...


class IFAQRepository(ABC):
    """Port for FAQ persistence."""

    @abstractmethod
    async def create(self, faq: FAQ) -> FAQ: ...

    @abstractmethod
    async def update(self, faq: FAQ) -> FAQ: ...

    @abstractmethod
    async def delete(self, faq_id: uuid.UUID, tenant_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: uuid.UUID, category: str | None = None) -> list[FAQ]: ...


@dataclass
class SearchResult:
    """A single search result from the vector store."""

    chunk_id: str
    document_id: str
    content: str
    score: float  # Similarity score (0.0 to 1.0)
    document_title: str
    metadata: dict


class IVectorStore(ABC):
    """Port for vector similarity search."""

    @abstractmethod
    async def store_embeddings(
        self, chunks: list[DocumentChunk]
    ) -> None:
        """Store chunk embeddings in the vector database."""
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        tenant_id: uuid.UUID,
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> list[SearchResult]:
        """Search for similar chunks by embedding vector."""
        ...

    @abstractmethod
    async def delete_by_document(
        self, document_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Remove all embeddings for a document."""
        ...


class IDocumentParser(ABC):
    """Port for document content extraction."""

    @abstractmethod
    async def parse(self, file_path: str, mime_type: str) -> str:
        """Extract text content from a file."""
        ...

    @abstractmethod
    def supported_types(self) -> list[str]:
        """Return list of supported MIME types."""
        ...
