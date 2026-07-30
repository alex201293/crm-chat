"""
RAG-enhanced message handler.
Searches the knowledge base before generating AI responses,
injecting relevant context into the AI prompt.
"""

import uuid
from dataclasses import dataclass

import structlog

from src.modules.ai.application.services.ai_service import AIService
from src.modules.ai.infrastructure.providers import OpenAIProvider
from src.modules.knowledge.application.queries import SearchKnowledgeHandler, SearchKnowledgeQuery
from src.modules.knowledge.infrastructure.vectorstore import PgVectorStore

logger = structlog.get_logger()


@dataclass
class RAGContext:
    """Context retrieved from the knowledge base for AI response generation."""

    documents: list[str]  # Chunk contents to inject into prompt
    sources: list[dict]  # Source metadata for attribution
    query: str


class KnowledgeRAGService:
    """
    Retrieval-Augmented Generation service.
    Bridges the Knowledge Base module and the AI Chat module.

    Flow:
    1. Receive user message
    2. Search knowledge base for relevant chunks
    3. Format chunks as context for the AI
    4. Return context for injection into the AI prompt
    """

    def __init__(self, session) -> None:
        self._session = session
        self._embedding_provider = OpenAIProvider()
        self._vector_store = PgVectorStore(session)

    async def retrieve_context(
        self,
        tenant_id: uuid.UUID,
        user_message: str,
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> RAGContext | None:
        """
        Search knowledge base for relevant context.
        Returns None if no relevant documents found.
        """
        try:
            handler = SearchKnowledgeHandler(
                vector_store=self._vector_store,
                embedding_provider=self._embedding_provider,
            )

            result = await handler.execute(
                SearchKnowledgeQuery(
                    tenant_id=tenant_id,
                    query=user_message,
                    top_k=top_k,
                    min_score=min_score,
                )
            )

            if not result.results:
                return None

            # Format context documents
            documents = []
            sources = []
            for r in result.results:
                documents.append(r.content)
                sources.append({
                    "document_title": r.document_title,
                    "document_id": r.document_id,
                    "score": r.score,
                })

            return RAGContext(
                documents=documents,
                sources=sources,
                query=user_message,
            )

        except Exception as e:
            logger.warning(
                "RAG context retrieval failed, continuing without context",
                error=str(e),
                tenant_id=str(tenant_id),
            )
            return None


class RAGEnhancedAIService:
    """
    AIService wrapper that integrates RAG context into responses.
    Drop-in replacement for AIService in the chat pipeline.
    """

    def __init__(
        self,
        ai_service: AIService,
        rag_service: KnowledgeRAGService,
    ) -> None:
        self._ai_service = ai_service
        self._rag_service = rag_service

    async def generate_response_with_context(
        self,
        tenant_id: uuid.UUID,
        user_message: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> tuple:
        """
        Generate AI response with RAG context injection.

        Returns:
            tuple: (CompletionResult, RAGContext | None)
        """
        # 1. Retrieve relevant context from knowledge base
        rag_context = await self._rag_service.retrieve_context(
            tenant_id=tenant_id,
            user_message=user_message,
        )

        # 2. Build context documents for AI
        context_documents = rag_context.documents if rag_context else []

        # 3. Enhance system prompt with RAG instructions
        enhanced_prompt = system_prompt
        if context_documents:
            enhanced_prompt += (
                "\n\nIMPORTANT: You have access to the company's knowledge base. "
                "Use the provided context to answer questions accurately. "
                "If the context contains the answer, use it. "
                "If the context doesn't cover the question, say so honestly. "
                "Always be helpful and concise."
            )

        # 4. Generate response with context
        result = await self._ai_service.generate_response(
            user_message=user_message,
            system_prompt=enhanced_prompt,
            conversation_history=conversation_history,
            context_documents=context_documents,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return result, rag_context
