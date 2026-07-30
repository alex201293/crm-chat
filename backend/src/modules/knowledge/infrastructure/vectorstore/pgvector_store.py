"""
pgvector-based vector store implementation.
Stores document chunk embeddings in PostgreSQL and performs similarity search.
"""

import uuid

import structlog
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, delete, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.knowledge.domain.entities.document import DocumentChunk
from src.modules.knowledge.domain.interfaces.repositories import IVectorStore, SearchResult
from src.shared.infrastructure.database.base import Base

logger = structlog.get_logger()


# =============================================================================
# ORM Model for document_chunks with pgvector
# =============================================================================
class DocumentChunkModel(Base):
    """
    SQLAlchemy model for document chunks with vector embeddings.
    Uses pgvector extension for similarity search.
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # pgvector column - defined via raw SQL since SQLAlchemy pgvector support varies
    # The actual vector column is created via migration with: vector(1536)


# =============================================================================
# Vector Store Implementation
# =============================================================================
class PgVectorStore(IVectorStore):
    """
    PostgreSQL + pgvector implementation of IVectorStore.
    Uses cosine similarity for search with tenant isolation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store_embeddings(self, chunks: list[DocumentChunk]) -> None:
        """Store chunk content and embeddings in the database."""
        for chunk in chunks:
            if not chunk.embedding:
                logger.warning("Chunk has no embedding, skipping", chunk_id=str(chunk.id))
                continue

            # Use raw SQL for pgvector insert since the vector type
            # requires special handling
            embedding_str = "[" + ",".join(str(v) for v in chunk.embedding) + "]"

            stmt = text("""
                INSERT INTO document_chunks (id, tenant_id, document_id, content, chunk_index, token_count, metadata, embedding)
                VALUES (:id, :tenant_id, :document_id, :content, :chunk_index, :token_count, :metadata::jsonb, :embedding::vector)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
            """)

            await self._session.execute(
                stmt,
                {
                    "id": str(chunk.id),
                    "tenant_id": str(chunk.tenant_id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    "metadata": "{}",
                    "embedding": embedding_str,
                },
            )

        await self._session.flush()
        logger.info("Stored embeddings", count=len(chunks))

    async def search(
        self,
        query_embedding: list[float],
        tenant_id: uuid.UUID,
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> list[SearchResult]:
        """
        Perform cosine similarity search against stored embeddings.
        Returns top_k results above min_score threshold.
        """
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Cosine similarity: 1 - cosine_distance
        # pgvector <=> operator returns cosine distance
        stmt = text("""
            SELECT
                dc.id,
                dc.document_id,
                dc.content,
                dc.metadata,
                1 - (dc.embedding <=> :query_embedding::vector) AS similarity,
                d.title AS document_title
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.tenant_id = :tenant_id
              AND 1 - (dc.embedding <=> :query_embedding::vector) >= :min_score
            ORDER BY dc.embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)

        result = await self._session.execute(
            stmt,
            {
                "query_embedding": embedding_str,
                "tenant_id": str(tenant_id),
                "min_score": min_score,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()

        return [
            SearchResult(
                chunk_id=str(row[0]),
                document_id=str(row[1]),
                content=row[2],
                metadata=row[3] or {},
                score=float(row[4]),
                document_title=row[5] or "",
            )
            for row in rows
        ]

    async def delete_by_document(
        self, document_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Remove all embeddings for a document."""
        stmt = text("""
            DELETE FROM document_chunks
            WHERE document_id = :document_id AND tenant_id = :tenant_id
        """)
        await self._session.execute(
            stmt,
            {"document_id": str(document_id), "tenant_id": str(tenant_id)},
        )
        await self._session.flush()
