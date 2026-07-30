"""Campaigns REST API endpoints."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.api.dependencies import CurrentUser
from src.modules.campaigns.application import (
    CreateCampaignCommand,
    CreateCampaignHandler,
    ExecuteCampaignHandler,
    GetCampaignStatsHandler,
    ListCampaignsHandler,
    PauseCampaignHandler,
    ScheduleCampaignCommand,
    ScheduleCampaignHandler,
    SendCampaignCommand,
)
from src.modules.campaigns.infrastructure import (
    CampaignDispatcher,
    CampaignMessageRepository,
    CampaignRepository,
    SegmentRepository,
)
from src.modules.campaigns.domain.entities import Segment
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================
class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    channel: str = Field(pattern="^(whatsapp|email|sms|telegram|facebook|instagram)$")
    template_content: str = Field(min_length=1)
    segment_id: str | None = None
    template_name: str | None = None
    subject: str | None = Field(default=None, max_length=500)


class ScheduleRequest(BaseModel):
    send_at: str  # ISO datetime


class CreateSegmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    filters: list[dict] = Field(min_length=1)


class CampaignResponse(BaseModel):
    id: str
    name: str
    channel: str
    status: str
    total_recipients: int
    sent_count: int
    delivered_count: int
    read_count: int
    clicked_count: int
    failed_count: int
    scheduled_at: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str


class SegmentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    filters: list[dict]
    contact_count: int
    is_dynamic: bool


class StatsResponse(BaseModel):
    total_recipients: int
    sent: int
    delivered: int
    read: int
    clicked: int
    failed: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    status_breakdown: dict[str, int]


# =============================================================================
# Campaign Endpoints
# =============================================================================
def _resp(c) -> CampaignResponse:
    return CampaignResponse(
        id=str(c.id), name=c.name, channel=c.channel.value, status=c.status.value,
        total_recipients=c.total_recipients, sent_count=c.sent_count,
        delivered_count=c.delivered_count, read_count=c.read_count,
        clicked_count=c.clicked_count, failed_count=c.failed_count,
        scheduled_at=c.scheduled_at.isoformat() if c.scheduled_at else None,
        started_at=c.started_at.isoformat() if c.started_at else None,
        completed_at=c.completed_at.isoformat() if c.completed_at else None,
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


@router.get("/", summary="List campaigns")
async def list_campaigns(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    handler = ListCampaignsHandler(CampaignRepository(session))
    campaigns, total = await handler.execute(
        current_user.tenant_id, status=status, page=page, page_size=page_size
    )
    return {
        "data": [_resp(c).model_dump() for c in campaigns],
        "total": total, "page": page, "page_size": page_size,
    }


@router.post("/", status_code=201, summary="Create campaign")
async def create_campaign(
    body: CreateCampaignRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    handler = CreateCampaignHandler(CampaignRepository(session))
    campaign = await handler.execute(CreateCampaignCommand(
        tenant_id=current_user.tenant_id,
        name=body.name, channel=body.channel,
        template_content=body.template_content,
        segment_id=uuid.UUID(body.segment_id) if body.segment_id else None,
        template_name=body.template_name, subject=body.subject,
    ))
    return _resp(campaign)


@router.post("/{campaign_id}/schedule", summary="Schedule campaign")
async def schedule_campaign(
    campaign_id: str,
    body: ScheduleRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    handler = ScheduleCampaignHandler(CampaignRepository(session))
    campaign = await handler.execute(ScheduleCampaignCommand(
        tenant_id=current_user.tenant_id,
        campaign_id=uuid.UUID(campaign_id),
        send_at=datetime.fromisoformat(body.send_at),
    ))
    return _resp(campaign)


@router.post("/{campaign_id}/send", summary="Send campaign now")
async def send_campaign(
    campaign_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    handler = ExecuteCampaignHandler(
        campaign_repo=CampaignRepository(session),
        segment_repo=SegmentRepository(session),
        message_repo=CampaignMessageRepository(session),
        dispatcher=CampaignDispatcher(),
    )
    campaign = await handler.execute(SendCampaignCommand(
        tenant_id=current_user.tenant_id, campaign_id=uuid.UUID(campaign_id)
    ))
    return _resp(campaign)


@router.post("/{campaign_id}/pause", summary="Pause campaign")
async def pause_campaign(
    campaign_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    handler = PauseCampaignHandler(CampaignRepository(session))
    await handler.execute(uuid.UUID(campaign_id), current_user.tenant_id)
    return {"message": "Campaign paused"}


@router.get("/{campaign_id}/stats", summary="Get campaign stats")
async def get_campaign_stats(
    campaign_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StatsResponse:
    handler = GetCampaignStatsHandler(
        CampaignRepository(session), CampaignMessageRepository(session)
    )
    stats = await handler.execute(uuid.UUID(campaign_id), current_user.tenant_id)
    return StatsResponse(
        total_recipients=stats.total_recipients, sent=stats.sent,
        delivered=stats.delivered, read=stats.read, clicked=stats.clicked,
        failed=stats.failed, delivery_rate=stats.delivery_rate,
        open_rate=stats.open_rate, click_rate=stats.click_rate,
        status_breakdown=stats.status_breakdown,
    )


# =============================================================================
# Segment Endpoints
# =============================================================================

@router.get("/segments", summary="List segments")
async def list_segments(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    repo = SegmentRepository(session)
    segments = await repo.list_by_tenant(current_user.tenant_id)
    return {
        "data": [
            SegmentResponse(
                id=str(s.id), name=s.name, description=s.description,
                filters=s.filters, contact_count=s.contact_count,
                is_dynamic=s.is_dynamic,
            ).model_dump() for s in segments
        ]
    }


@router.post("/segments", status_code=201, summary="Create segment")
async def create_segment(
    body: CreateSegmentRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SegmentResponse:
    repo = SegmentRepository(session)
    segment = Segment.create(
        tenant_id=current_user.tenant_id,
        name=body.name, filters=body.filters,
        description=body.description,
    )
    # Evaluate contact count
    contact_ids = await repo.get_contact_ids(segment.id, current_user.tenant_id)
    segment.contact_count = len(contact_ids)
    await repo.create(segment)
    return SegmentResponse(
        id=str(segment.id), name=segment.name,
        description=segment.description, filters=segment.filters,
        contact_count=segment.contact_count, is_dynamic=segment.is_dynamic,
    )


@router.delete("/segments/{segment_id}", summary="Delete segment")
async def delete_segment(
    segment_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    repo = SegmentRepository(session)
    await repo.delete(uuid.UUID(segment_id), current_user.tenant_id)
    return {"message": "Segment deleted"}
