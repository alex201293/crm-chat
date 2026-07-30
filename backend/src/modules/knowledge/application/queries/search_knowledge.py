"""
Use case: Search the knowledge base using semantic similarity.
Used both by the API directly and by the AI chat pipeline (RAG).
"""

import uuid
from dataclasses import dataclass

from src.modules.ai.domain.interfaces import IEmbeddingProvider
from src.modules.knowledge.domain.interfaces.repositories import IVectorStore, SearchResult


@dataclass
class SearchKnowledgeQuery:
    tenant_id: uuid.UUID
    query: str
    top_k: int = 5
    min_score: float = 0.7


@dataclass
class SearchResultDTO:
    content: str
    score: float
    document_title: str
    document_id: str
    chunk_id: str


@dataclass
class SearchKnowledgeResult:
    results: list[SearchResultDTO]
    query: str


class SearchKnowledgeHandler:
    """
    Semantic search over the tenant's knowledge base.
    1. Embed the query
    2. Search vector store for similar chunks
    3. Return ranked results
    """

    def __init__(
        self,
        vector_store: IVectorStore,
        embedding_provider: IEmbeddingProvider,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider

    async def execute(self, query: SearchKnowledgeQuery) -> SearchKnowledgeResult:
        # Generate query embedding
        query_embedding = await self._embedding_provider.embed_single(query.query)

        # Search vector store
        results = await self._vector_store.search(
            query_embedding=query_embedding,
            tenant_id=query.tenant_id,
            top_k=query.top_k,
            min_score=query.min_score,
        )

        return SearchKnowledgeResult(
            results=[
                SearchResultDTO(
                    content=r.content,
                    score=r.score,
                    document_title=r.document_title,
                    document_id=r.document_id,
                    chunk_id=r.chunk_id,
                )
                for r in results
            ],
            query=query.query,
        )
