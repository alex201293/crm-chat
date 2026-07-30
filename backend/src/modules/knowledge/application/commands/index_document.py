"""
Use cases for uploading, indexing, and managing knowledge base documents.
"""

import uuid
from dataclasses import dataclass

import structlog

from src.modules.ai.domain.interfaces import IEmbeddingProvider
from src.modules.knowledge.domain.entities.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
)
from src.modules.knowledge.domain.interfaces.repositories import (
    IDocumentRepository,
    IVectorStore,
)
from src.modules.knowledge.infrastructure.parsers import (
    DocumentParser,
    TextChunker,
    WebPageParser,
)
from src.shared.api.exceptions import EntityNotFoundError, ValidationError_

logger = structlog.get_logger()


# =============================================================================
# Upload Document
# =============================================================================
@dataclass
class UploadDocumentCommand:
    tenant_id: uuid.UUID
    title: str
    file_path: str
    file_size: int
    mime_type: str
    document_type: str  # "pdf", "docx", "xlsx", "txt", "html"


@dataclass
class UploadDocumentResult:
    document_id: str
    title: str
    status: str


class UploadDocumentHandler:
    """Upload a file and prepare it for indexing."""

    def __init__(self, document_repo: IDocumentRepository) -> None:
        self._document_repo = document_repo

    async def execute(self, command: UploadDocumentCommand) -> UploadDocumentResult:
        doc_type = DocumentType(command.document_type)

        document = Document.create_from_file(
            tenant_id=command.tenant_id,
            title=command.title,
            document_type=doc_type,
            file_path=command.file_path,
            file_size=command.file_size,
            mime_type=command.mime_type,
        )
        await self._document_repo.create(document)

        return UploadDocumentResult(
            document_id=str(document.id),
            title=document.title,
            status=document.status.value,
        )


# =============================================================================
# Index Document (parse + chunk + embed + store)
# =============================================================================
@dataclass
class IndexDocumentCommand:
    tenant_id: uuid.UUID
    document_id: uuid.UUID


class IndexDocumentHandler:
    """
    Full indexing pipeline:
    1. Parse document to text
    2. Chunk text with overlap
    3. Generate embeddings for each chunk
    4. Store embeddings in vector store
    5. Update document status
    """

    def __init__(
        self,
        document_repo: IDocumentRepository,
        vector_store: IVectorStore,
        embedding_provider: IEmbeddingProvider,
    ) -> None:
        self._document_repo = document_repo
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._parser = DocumentParser()
        self._chunker = TextChunker()

    async def execute(self, command: IndexDocumentCommand) -> None:
        document = await self._document_repo.get_by_id(
            command.document_id, command.tenant_id
        )
        if not document:
            raise EntityNotFoundError("Document", str(command.document_id))

        document.mark_processing()
        await self._document_repo.update(document)

        try:
            # 1. Parse document
            if document.document_type == DocumentType.URL:
                parser = WebPageParser()
                text_content = await parser.fetch_and_parse(document.source_url or "")
            else:
                text_content = await self._parser.parse(
                    document.file_path or "", document.mime_type or ""
                )

            if not text_content.strip():
                document.mark_failed("No text content extracted from document")
                await self._document_repo.update(document)
                return

            # 2. Chunk text
            text_chunks = self._chunker.chunk_text(text_content)

            if not text_chunks:
                document.mark_failed("Document produced no chunks after splitting")
                await self._document_repo.update(document)
                return

            # 3. Generate embeddings in batches
            batch_size = 50
            all_chunks: list[DocumentChunk] = []

            for i in range(0, len(text_chunks), batch_size):
                batch = text_chunks[i : i + batch_size]
                texts = [chunk.content for chunk in batch]

                embedding_result = await self._embedding_provider.embed(texts)

                for j, text_chunk in enumerate(batch):
                    doc_chunk = DocumentChunk.create(
                        tenant_id=command.tenant_id,
                        document_id=command.document_id,
                        content=text_chunk.content,
                        chunk_index=text_chunk.index,
                        token_count=text_chunk.token_count,
                        metadata={
                            "document_title": document.title,
                            "start_char": text_chunk.start_char,
                            "end_char": text_chunk.end_char,
                        },
                    )
                    doc_chunk.embedding = embedding_result.embeddings[j]
                    all_chunks.append(doc_chunk)

            # 4. Store in vector store
            await self._vector_store.store_embeddings(all_chunks)

            # 5. Update document status
            document.mark_indexed(
                chunk_count=len(all_chunks),
                character_count=len(text_content),
            )
            await self._document_repo.update(document)

            logger.info(
                "Document indexed successfully",
                document_id=str(command.document_id),
                chunks=len(all_chunks),
                characters=len(text_content),
            )

        except Exception as e:
            logger.error(
                "Document indexing failed",
                document_id=str(command.document_id),
                error=str(e),
            )
            document.mark_failed(str(e)[:500])
            await self._document_repo.update(document)
            raise


# =============================================================================
# Index URL
# =============================================================================
@dataclass
class IndexURLCommand:
    tenant_id: uuid.UUID
    title: str
    url: str


class IndexURLHandler:
    """Create a document from URL and index it."""

    def __init__(
        self,
        document_repo: IDocumentRepository,
        vector_store: IVectorStore,
        embedding_provider: IEmbeddingProvider,
    ) -> None:
        self._document_repo = document_repo
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider

    async def execute(self, command: IndexURLCommand) -> UploadDocumentResult:
        document = Document.create_from_url(
            tenant_id=command.tenant_id,
            title=command.title,
            source_url=command.url,
        )
        await self._document_repo.create(document)

        # Immediately index
        indexer = IndexDocumentHandler(
            document_repo=self._document_repo,
            vector_store=self._vector_store,
            embedding_provider=self._embedding_provider,
        )
        await indexer.execute(
            IndexDocumentCommand(
                tenant_id=command.tenant_id,
                document_id=document.id,
            )
        )

        # Reload to get updated status
        updated = await self._document_repo.get_by_id(document.id, command.tenant_id)

        return UploadDocumentResult(
            document_id=str(document.id),
            title=document.title,
            status=updated.status.value if updated else "failed",
        )


# =============================================================================
# Delete Document
# =============================================================================
@dataclass
class DeleteDocumentCommand:
    tenant_id: uuid.UUID
    document_id: uuid.UUID


class DeleteDocumentHandler:
    """Delete a document and its embeddings."""

    def __init__(
        self,
        document_repo: IDocumentRepository,
        vector_store: IVectorStore,
    ) -> None:
        self._document_repo = document_repo
        self._vector_store = vector_store

    async def execute(self, command: DeleteDocumentCommand) -> None:
        document = await self._document_repo.get_by_id(
            command.document_id, command.tenant_id
        )
        if not document:
            raise EntityNotFoundError("Document", str(command.document_id))

        # Remove embeddings
        await self._vector_store.delete_by_document(
            command.document_id, command.tenant_id
        )

        # Remove document
        await self._document_repo.delete(command.document_id, command.tenant_id)
