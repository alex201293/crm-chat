"""
Knowledge Base API endpoints.
Manages documents, FAQs, and semantic search.
"""

import os
import uuid
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.api.dependencies import CurrentUser
# OpenAIProvider imported lazily where needed
from src.modules.knowledge.application.commands import (
    DeleteDocumentCommand,
    DeleteDocumentHandler,
    IndexDocumentCommand,
    IndexDocumentHandler,
    IndexURLCommand,
    IndexURLHandler,
    UploadDocumentCommand,
    UploadDocumentHandler,
)
from src.modules.knowledge.application.queries import (
    SearchKnowledgeHandler,
    SearchKnowledgeQuery,
)
from src.modules.knowledge.domain.entities.document import FAQ
from src.modules.knowledge.infrastructure.repositories import (
    DocumentRepository,
    FAQRepository,
)
from src.modules.knowledge.infrastructure.vectorstore import PgVectorStore
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()

UPLOAD_DIR = "./storage/knowledge"


# =============================================================================
# Schemas
# =============================================================================
class IndexURLRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2000)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.7, ge=0.0, le=1.0)


class CreateFAQRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=5000)
    category: str | None = Field(default=None, max_length=100)


class DocumentResponse(BaseModel):
    id: str
    title: str
    document_type: str
    status: str
    chunk_count: int
    character_count: int
    file_size: int
    source_url: str | None
    error_message: str | None
    created_at: str


class SearchResultResponse(BaseModel):
    content: str
    score: float
    document_title: str
    document_id: str


class FAQResponse(BaseModel):
    id: str
    question: str
    answer: str
    category: str | None
    order: int


# =============================================================================
# Document Endpoints
# =============================================================================


@router.post("/documents/upload", status_code=201, summary="Upload a document")
async def upload_document(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    title: str = Form(""),
) -> DocumentResponse:
    """Upload a file (PDF, DOCX, XLSX, TXT, HTML) to the knowledge base."""
    # Validate file type
    allowed_mimes = {
        "application/pdf", "text/plain", "text/html", "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    if file.content_type not in allowed_mimes:
        from src.shared.api.exceptions import ValidationError_
        raise ValidationError_(f"Unsupported file type: {file.content_type}", field="file")

    # Determine document type from mime
    mime_to_type = {
        "application/pdf": "pdf",
        "text/plain": "txt",
        "text/html": "html",
        "text/csv": "txt",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    }
    doc_type = mime_to_type.get(file.content_type, "txt")

    # Save file
    tenant_dir = os.path.join(UPLOAD_DIR, str(current_user.tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    extension = os.path.splitext(file.filename or "file")[1] or f".{doc_type}"
    file_path = os.path.join(tenant_dir, f"{file_id}{extension}")

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    file_size = len(content)
    doc_title = title or file.filename or "Untitled"

    # Create document record
    handler = UploadDocumentHandler(DocumentRepository(session))
    result = await handler.execute(
        UploadDocumentCommand(
            tenant_id=current_user.tenant_id,
            title=doc_title,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type or "",
            document_type=doc_type,
        )
    )

    # Auto-index
    # Auto-index (skip if no embedding provider available)
    try:
        from src.modules.ai.infrastructure.providers import OpenAIProvider as _OAI
        if _OAI:
            embedding_provider = _OAI()
            index_handler = IndexDocumentHandler(
                document_repo=DocumentRepository(session),
                vector_store=PgVectorStore(session),
                embedding_provider=embedding_provider,
            )
            await index_handler.execute(
                IndexDocumentCommand(
                    tenant_id=current_user.tenant_id,
                    document_id=uuid.UUID(result.document_id),
                )
            )
    except Exception:
        pass  # Indexing not available, document stored without embeddings

    # Reload document for current status
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(uuid.UUID(result.document_id), current_user.tenant_id)

    return DocumentResponse(
        id=result.document_id,
        title=result.title,
        document_type=doc_type,
        status=doc.status.value if doc else result.status,
        chunk_count=doc.chunk_count if doc else 0,
        character_count=doc.character_count if doc else 0,
        file_size=file_size,
        source_url=None,
        error_message=doc.error_message if doc else None,
        created_at=doc.created_at.isoformat() if doc and doc.created_at else "",
    )


@router.post("/documents/url", status_code=201, summary="Index a web page")
async def index_url(
    body: IndexURLRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentResponse:
    """Fetch and index a web page into the knowledge base."""
    embedding_provider = None  # No embedding provider available
    handler = IndexURLHandler(
        document_repo=DocumentRepository(session),
        vector_store=PgVectorStore(session),
        embedding_provider=embedding_provider,
    )

    result = await handler.execute(
        IndexURLCommand(
            tenant_id=current_user.tenant_id,
            title=body.title,
            url=body.url,
        )
    )

    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(uuid.UUID(result.document_id), current_user.tenant_id)

    return DocumentResponse(
        id=result.document_id,
        title=result.title,
        document_type="url",
        status=doc.status.value if doc else result.status,
        chunk_count=doc.chunk_count if doc else 0,
        character_count=doc.character_count if doc else 0,
        file_size=0,
        source_url=body.url,
        error_message=doc.error_message if doc else None,
        created_at=doc.created_at.isoformat() if doc and doc.created_at else "",
    )


@router.get("/documents", summary="List documents")
async def list_documents(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List all documents in the knowledge base."""
    from src.modules.knowledge.domain.entities.document import DocumentStatus as DS

    doc_repo = DocumentRepository(session)
    doc_status = DS(status) if status else None
    offset = (page - 1) * page_size

    documents = await doc_repo.list_by_tenant(
        current_user.tenant_id, status=doc_status, offset=offset, limit=page_size
    )
    total = await doc_repo.count_by_tenant(current_user.tenant_id)

    return {
        "data": [
            DocumentResponse(
                id=str(d.id),
                title=d.title,
                document_type=d.document_type.value,
                status=d.status.value,
                chunk_count=d.chunk_count,
                character_count=d.character_count,
                file_size=d.file_size,
                source_url=d.source_url,
                error_message=d.error_message,
                created_at=d.created_at.isoformat() if d.created_at else "",
            ).model_dump()
            for d in documents
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/documents/{document_id}", summary="Delete a document")
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Delete a document and its embeddings from the knowledge base."""
    handler = DeleteDocumentHandler(
        document_repo=DocumentRepository(session),
        vector_store=PgVectorStore(session),
    )
    await handler.execute(
        DeleteDocumentCommand(
            tenant_id=current_user.tenant_id,
            document_id=uuid.UUID(document_id),
        )
    )
    return {"message": "Document deleted successfully"}


# =============================================================================
# Search
# =============================================================================


@router.post("/search", summary="Search the knowledge base")
async def search_knowledge(
    body: SearchRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Perform semantic search over the knowledge base."""
    embedding_provider = None  # No embedding provider available
    handler = SearchKnowledgeHandler(
        vector_store=PgVectorStore(session),
        embedding_provider=embedding_provider,
    )

    result = await handler.execute(
        SearchKnowledgeQuery(
            tenant_id=current_user.tenant_id,
            query=body.query,
            top_k=body.top_k,
            min_score=body.min_score,
        )
    )

    return {
        "query": result.query,
        "results": [
            SearchResultResponse(
                content=r.content,
                score=r.score,
                document_title=r.document_title,
                document_id=r.document_id,
            ).model_dump()
            for r in result.results
        ],
    }


# =============================================================================
# FAQs
# =============================================================================


@router.get("/faqs", summary="List FAQs")
async def list_faqs(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    category: str | None = Query(default=None),
) -> dict:
    """List all active FAQs for the tenant."""
    faq_repo = FAQRepository(session)
    faqs = await faq_repo.list_by_tenant(current_user.tenant_id, category=category)

    return {
        "data": [
            FAQResponse(
                id=str(f.id), question=f.question, answer=f.answer,
                category=f.category, order=f.order,
            ).model_dump()
            for f in faqs
        ]
    }


@router.post("/faqs", status_code=201, summary="Create a FAQ")
async def create_faq(
    body: CreateFAQRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FAQResponse:
    """Create a new FAQ entry."""
    faq_repo = FAQRepository(session)
    faq = FAQ(
        tenant_id=current_user.tenant_id,
        question=body.question,
        answer=body.answer,
        category=body.category,
    )
    await faq_repo.create(faq)

    return FAQResponse(
        id=str(faq.id), question=faq.question, answer=faq.answer,
        category=faq.category, order=faq.order,
    )


@router.delete("/faqs/{faq_id}", summary="Delete a FAQ")
async def delete_faq(
    faq_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Delete a FAQ entry."""
    faq_repo = FAQRepository(session)
    await faq_repo.delete(uuid.UUID(faq_id), current_user.tenant_id)
    return {"message": "FAQ deleted"}
