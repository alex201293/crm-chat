"""CRM REST API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.api.dependencies import CurrentUser
from src.modules.crm.api.schemas import (
    CompanyResponse,
    ContactResponse,
    CreateCompanyRequest,
    CreateContactRequest,
    CreateDealRequest,
    CreateNoteRequest,
    CreateTaskRequest,
    DealResponse,
    LoseDealRequest,
    MoveDealStageRequest,
    NoteResponse,
    PipelineResponse,
    StageResponse,
    TaskResponse,
    UpdateContactRequest,
)
from src.modules.crm.application.commands import (
    CreateContactCommand,
    CreateContactHandler,
    CreateDealCommand,
    CreateDealHandler,
    CreateDefaultPipelineCommand,
    CreateDefaultPipelineHandler,
    CreateTaskCommand,
    CreateTaskHandler,
    CompleteTaskCommand,
    CompleteTaskHandler,
    LoseDealCommand,
    LoseDealHandler,
    MoveDealStageCommand,
    MoveDealStageHandler,
    UpdateContactCommand,
    UpdateContactHandler,
    WinDealCommand,
    WinDealHandler,
)
from src.modules.crm.application.queries import (
    GetContactsHandler,
    GetContactsQuery,
    GetDealsHandler,
    GetDealsQuery,
    GetPipelineHandler,
    GetPipelineQuery,
)
from src.modules.crm.infrastructure.repositories import *
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


# =============================================================================
# Contacts
# =============================================================================

@router.get("/contacts", summary="List contacts")
async def list_contacts(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: str | None = Query(default=None),
    lifecycle_stage: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    handler = GetContactsHandler(ContactRepository(session))
    contacts, total = await handler.execute(
        GetContactsQuery(
            tenant_id=current_user.tenant_id,
            search=search,
            lifecycle_stage=lifecycle_stage,
            page=page,
            page_size=page_size,
        )
    )
    return {
        "data": [
            ContactResponse(
                id=str(c.id), full_name=c.full_name, email=c.email,
                phone=c.phone, company_id=str(c.company_id) if c.company_id else None,
                lifecycle_stage=c.lifecycle_stage.value, tags=c.tags,
                source=c.source, total_conversations=c.total_conversations,
                total_messages=c.total_messages,
                last_seen_at=c.last_seen_at.isoformat() if c.last_seen_at else None,
                created_at=c.created_at.isoformat() if c.created_at else "",
            ).model_dump() for c in contacts
        ],
        "total": total, "page": page, "page_size": page_size,
    }


@router.post("/contacts", status_code=201, summary="Create contact")
async def create_contact(
    body: CreateContactRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContactResponse:
    handler = CreateContactHandler(
        ContactRepository(session), ActivityRepository(session)
    )
    contact = await handler.execute(CreateContactCommand(
        tenant_id=current_user.tenant_id,
        full_name=body.full_name, email=body.email, phone=body.phone,
        company_id=uuid.UUID(body.company_id) if body.company_id else None,
        source=body.source, tags=body.tags, custom_fields=body.custom_fields,
    ))
    return ContactResponse(
        id=str(contact.id), full_name=contact.full_name, email=contact.email,
        phone=contact.phone,
        company_id=str(contact.company_id) if contact.company_id else None,
        lifecycle_stage=contact.lifecycle_stage.value, tags=contact.tags,
        source=contact.source, total_conversations=0, total_messages=0,
        last_seen_at=None,
        created_at=contact.created_at.isoformat() if contact.created_at else "",
    )


@router.get("/contacts/{contact_id}", summary="Get contact")
async def get_contact(
    contact_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContactResponse:
    from src.shared.api.exceptions import EntityNotFoundError
    repo = ContactRepository(session)
    contact = await repo.get_by_id(uuid.UUID(contact_id), current_user.tenant_id)
    if not contact:
        raise EntityNotFoundError("Contact", contact_id)
    return ContactResponse(
        id=str(contact.id), full_name=contact.full_name, email=contact.email,
        phone=contact.phone,
        company_id=str(contact.company_id) if contact.company_id else None,
        lifecycle_stage=contact.lifecycle_stage.value, tags=contact.tags,
        source=contact.source, total_conversations=contact.total_conversations,
        total_messages=contact.total_messages,
        last_seen_at=contact.last_seen_at.isoformat() if contact.last_seen_at else None,
        created_at=contact.created_at.isoformat() if contact.created_at else "",
    )


@router.patch("/contacts/{contact_id}", summary="Update contact")
async def update_contact(
    contact_id: str,
    body: UpdateContactRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContactResponse:
    handler = UpdateContactHandler(ContactRepository(session))
    contact = await handler.execute(UpdateContactCommand(
        tenant_id=current_user.tenant_id,
        contact_id=uuid.UUID(contact_id),
        full_name=body.full_name, email=body.email, phone=body.phone,
        company_id=uuid.UUID(body.company_id) if body.company_id else None,
        lifecycle_stage=body.lifecycle_stage, tags=body.tags,
        custom_fields=body.custom_fields, country=body.country,
        city=body.city, language=body.language,
    ))
    return ContactResponse(
        id=str(contact.id), full_name=contact.full_name, email=contact.email,
        phone=contact.phone,
        company_id=str(contact.company_id) if contact.company_id else None,
        lifecycle_stage=contact.lifecycle_stage.value, tags=contact.tags,
        source=contact.source, total_conversations=contact.total_conversations,
        total_messages=contact.total_messages,
        last_seen_at=contact.last_seen_at.isoformat() if contact.last_seen_at else None,
        created_at=contact.created_at.isoformat() if contact.created_at else "",
    )


@router.delete("/contacts/{contact_id}", summary="Delete contact")
async def delete_contact(
    contact_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    repo = ContactRepository(session)
    await repo.delete(uuid.UUID(contact_id), current_user.tenant_id)
    return {"message": "Contact deleted"}


# =============================================================================
# Pipeline & Deals
# =============================================================================

@router.get("/pipelines", summary="List pipelines")
async def list_pipelines(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    repo = PipelineRepository(session)
    pipelines = await repo.list_by_tenant(current_user.tenant_id)
    return {
        "data": [
            PipelineResponse(
                id=str(p.id), name=p.name, is_default=p.is_default, is_active=p.is_active,
                stages=[StageResponse(
                    id=str(s.id), name=s.name, color=s.color, order=s.order,
                    is_won=s.is_won, is_lost=s.is_lost, probability=s.probability,
                ) for s in p.stages],
            ).model_dump() for p in pipelines
        ]
    }


@router.post("/pipelines/default", status_code=201, summary="Create default pipeline")
async def create_default_pipeline(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PipelineResponse:
    handler = CreateDefaultPipelineHandler(PipelineRepository(session))
    pipeline = await handler.execute(
        CreateDefaultPipelineCommand(tenant_id=current_user.tenant_id)
    )
    return PipelineResponse(
        id=str(pipeline.id), name=pipeline.name,
        is_default=pipeline.is_default, is_active=pipeline.is_active,
        stages=[StageResponse(
            id=str(s.id), name=s.name, color=s.color, order=s.order,
            is_won=s.is_won, is_lost=s.is_lost, probability=s.probability,
        ) for s in pipeline.stages],
    )


@router.get("/pipelines/{pipeline_id}/deals", summary="List deals in pipeline")
async def list_deals(
    pipeline_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(default=None),
    stage_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    handler = GetDealsHandler(DealRepository(session))
    deals, total = await handler.execute(GetDealsQuery(
        tenant_id=current_user.tenant_id,
        pipeline_id=uuid.UUID(pipeline_id),
        status=status,
        stage_id=uuid.UUID(stage_id) if stage_id else None,
        page=page, page_size=page_size,
    ))
    return {
        "data": [
            DealResponse(
                id=str(d.id), pipeline_id=str(d.pipeline_id),
                stage_id=str(d.stage_id) if d.stage_id else None,
                title=d.title, value=d.value, currency=d.currency,
                probability=d.probability, status=d.status.value,
                contact_id=str(d.contact_id) if d.contact_id else None,
                company_id=str(d.company_id) if d.company_id else None,
                assigned_to_id=str(d.assigned_to_id) if d.assigned_to_id else None,
                expected_close_date=d.expected_close_date.isoformat() if d.expected_close_date else None,
                won_at=d.won_at.isoformat() if d.won_at else None,
                lost_at=d.lost_at.isoformat() if d.lost_at else None,
                lost_reason=d.lost_reason, tags=d.tags,
                created_at=d.created_at.isoformat() if d.created_at else "",
            ).model_dump() for d in deals
        ],
        "total": total, "page": page, "page_size": page_size,
    }


@router.post("/deals", status_code=201, summary="Create deal")
async def create_deal(
    body: CreateDealRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DealResponse:
    from datetime import datetime
    handler = CreateDealHandler(
        DealRepository(session), PipelineRepository(session), ActivityRepository(session)
    )
    deal = await handler.execute(CreateDealCommand(
        tenant_id=current_user.tenant_id, title=body.title,
        pipeline_id=uuid.UUID(body.pipeline_id) if body.pipeline_id else None,
        stage_id=uuid.UUID(body.stage_id) if body.stage_id else None,
        value=body.value, currency=body.currency,
        contact_id=uuid.UUID(body.contact_id) if body.contact_id else None,
        company_id=uuid.UUID(body.company_id) if body.company_id else None,
        assigned_to_id=uuid.UUID(body.assigned_to_id) if body.assigned_to_id else None,
        expected_close_date=datetime.fromisoformat(body.expected_close_date) if body.expected_close_date else None,
    ))
    return DealResponse(
        id=str(deal.id), pipeline_id=str(deal.pipeline_id),
        stage_id=str(deal.stage_id) if deal.stage_id else None,
        title=deal.title, value=deal.value, currency=deal.currency,
        probability=deal.probability, status=deal.status.value,
        contact_id=str(deal.contact_id) if deal.contact_id else None,
        company_id=str(deal.company_id) if deal.company_id else None,
        assigned_to_id=str(deal.assigned_to_id) if deal.assigned_to_id else None,
        expected_close_date=deal.expected_close_date.isoformat() if deal.expected_close_date else None,
        won_at=None, lost_at=None, lost_reason=None, tags=deal.tags,
        created_at=deal.created_at.isoformat() if deal.created_at else "",
    )


@router.post("/deals/{deal_id}/move", summary="Move deal to stage")
async def move_deal_stage(
    deal_id: str, body: MoveDealStageRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    handler = MoveDealStageHandler(
        DealRepository(session), PipelineRepository(session), ActivityRepository(session)
    )
    await handler.execute(MoveDealStageCommand(
        tenant_id=current_user.tenant_id,
        deal_id=uuid.UUID(deal_id),
        new_stage_id=uuid.UUID(body.stage_id),
    ))
    return {"message": "Deal moved successfully"}


@router.post("/deals/{deal_id}/win", summary="Mark deal as won")
async def win_deal(
    deal_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    handler = WinDealHandler(DealRepository(session), ActivityRepository(session))
    await handler.execute(WinDealCommand(
        tenant_id=current_user.tenant_id, deal_id=uuid.UUID(deal_id)
    ))
    return {"message": "Deal marked as won"}


@router.post("/deals/{deal_id}/lose", summary="Mark deal as lost")
async def lose_deal(
    deal_id: str, body: LoseDealRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    handler = LoseDealHandler(DealRepository(session), ActivityRepository(session))
    await handler.execute(LoseDealCommand(
        tenant_id=current_user.tenant_id,
        deal_id=uuid.UUID(deal_id), reason=body.reason,
    ))
    return {"message": "Deal marked as lost"}


# =============================================================================
# Tasks
# =============================================================================

@router.get("/tasks", summary="List tasks")
async def list_tasks(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    contact_id: str | None = Query(default=None),
    deal_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    from src.modules.crm.domain.value_objects import TaskStatus
    repo = TaskRepository(session)
    tasks = await repo.list_by_tenant(
        tenant_id=current_user.tenant_id,
        assigned_to=uuid.UUID(assigned_to) if assigned_to else None,
        status=TaskStatus(status) if status else None,
        contact_id=uuid.UUID(contact_id) if contact_id else None,
        deal_id=uuid.UUID(deal_id) if deal_id else None,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return {
        "data": [
            TaskResponse(
                id=str(t.id), title=t.title, description=t.description,
                status=t.status.value, priority=t.priority.value,
                assigned_to_id=str(t.assigned_to_id) if t.assigned_to_id else None,
                contact_id=str(t.contact_id) if t.contact_id else None,
                deal_id=str(t.deal_id) if t.deal_id else None,
                due_date=t.due_date.isoformat() if t.due_date else None,
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
                created_at=t.created_at.isoformat() if t.created_at else "",
            ).model_dump() for t in tasks
        ],
        "total": len(tasks), "page": page, "page_size": page_size,
    }


@router.post("/tasks", status_code=201, summary="Create task")
async def create_task(
    body: CreateTaskRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    from datetime import datetime
    handler = CreateTaskHandler(TaskRepository(session))
    task = await handler.execute(CreateTaskCommand(
        tenant_id=current_user.tenant_id, title=body.title,
        description=body.description,
        assigned_to_id=uuid.UUID(body.assigned_to_id) if body.assigned_to_id else None,
        contact_id=uuid.UUID(body.contact_id) if body.contact_id else None,
        deal_id=uuid.UUID(body.deal_id) if body.deal_id else None,
        due_date=datetime.fromisoformat(body.due_date) if body.due_date else None,
        priority=body.priority,
    ))
    return TaskResponse(
        id=str(task.id), title=task.title, description=task.description,
        status=task.status.value, priority=task.priority.value,
        assigned_to_id=str(task.assigned_to_id) if task.assigned_to_id else None,
        contact_id=str(task.contact_id) if task.contact_id else None,
        deal_id=str(task.deal_id) if task.deal_id else None,
        due_date=task.due_date.isoformat() if task.due_date else None,
        completed_at=None,
        created_at=task.created_at.isoformat() if task.created_at else "",
    )


@router.post("/tasks/{task_id}/complete", summary="Complete task")
async def complete_task(
    task_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    handler = CompleteTaskHandler(TaskRepository(session), ActivityRepository(session))
    await handler.execute(CompleteTaskCommand(
        tenant_id=current_user.tenant_id, task_id=uuid.UUID(task_id)
    ))
    return {"message": "Task completed"}


# =============================================================================
# Notes
# =============================================================================

@router.post("/notes", status_code=201, summary="Create note")
async def create_note(
    body: CreateNoteRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NoteResponse:
    from src.modules.crm.domain.entities.note import Note
    repo = NoteRepository(session)
    note = Note.create(
        tenant_id=current_user.tenant_id,
        author_id=current_user.id,
        content=body.content,
        contact_id=uuid.UUID(body.contact_id) if body.contact_id else None,
        deal_id=uuid.UUID(body.deal_id) if body.deal_id else None,
    )
    await repo.create(note)
    return NoteResponse(
        id=str(note.id), content=note.content, is_pinned=note.is_pinned,
        author_id=str(note.author_id) if note.author_id else None,
        contact_id=str(note.contact_id) if note.contact_id else None,
        deal_id=str(note.deal_id) if note.deal_id else None,
        created_at=note.created_at.isoformat() if note.created_at else "",
    )


@router.get("/contacts/{contact_id}/notes", summary="Get contact notes")
async def get_contact_notes(
    contact_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    repo = NoteRepository(session)
    notes = await repo.list_by_contact(
        uuid.UUID(contact_id), current_user.tenant_id
    )
    return {
        "data": [
            NoteResponse(
                id=str(n.id), content=n.content, is_pinned=n.is_pinned,
                author_id=str(n.author_id) if n.author_id else None,
                contact_id=str(n.contact_id) if n.contact_id else None,
                deal_id=str(n.deal_id) if n.deal_id else None,
                created_at=n.created_at.isoformat() if n.created_at else "",
            ).model_dump() for n in notes
        ]
    }


# =============================================================================
# Activities
# =============================================================================

@router.get("/contacts/{contact_id}/activities", summary="Get contact timeline")
async def get_contact_activities(
    contact_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    from src.modules.crm.api.schemas import ActivityResponse
    repo = ActivityRepository(session)
    activities = await repo.list_by_contact(
        uuid.UUID(contact_id), current_user.tenant_id
    )
    return {
        "data": [
            ActivityResponse(
                id=str(a.id), activity_type=a.activity_type.value,
                title=a.title, description=a.description,
                user_id=str(a.user_id) if a.user_id else None,
                created_at=a.created_at.isoformat() if a.created_at else "",
            ).model_dump() for a in activities
        ]
    }


# =============================================================================
# Companies
# =============================================================================

@router.post("/companies", status_code=201, summary="Create company")
async def create_company(
    body: CreateCompanyRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyResponse:
    from src.modules.crm.domain.entities.company import Company
    repo = CompanyRepository(session)
    company = Company.create(
        tenant_id=current_user.tenant_id,
        name=body.name, domain=body.domain, industry=body.industry,
    )
    company.size = body.size
    company.website = body.website
    company.phone = body.phone
    company.country = body.country
    await repo.create(company)
    return CompanyResponse(
        id=str(company.id), name=company.name, domain=company.domain,
        industry=company.industry, size=company.size,
        website=company.website, country=company.country,
        created_at=company.created_at.isoformat() if company.created_at else "",
    )


@router.get("/companies", summary="List companies")
async def list_companies(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    repo = CompanyRepository(session)
    companies = await repo.list_by_tenant(
        current_user.tenant_id, search=search,
        offset=(page - 1) * page_size, limit=page_size,
    )
    total = await repo.count_by_tenant(current_user.tenant_id)
    return {
        "data": [
            CompanyResponse(
                id=str(c.id), name=c.name, domain=c.domain,
                industry=c.industry, size=c.size,
                website=c.website, country=c.country,
                created_at=c.created_at.isoformat() if c.created_at else "",
            ).model_dump() for c in companies
        ],
        "total": total, "page": page, "page_size": page_size,
    }
