"""
Agent Panel API endpoints.
Provides real-time metrics, conversation queue, SLA tracking,
agent performance, satisfaction scores, and presence status.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case, extract
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.modules.auth.api.dependencies import CurrentUser
from src.modules.chat.infrastructure.models import (
    ConversationModel,
    MessageModel,
    ConversationAssignmentModel,
)
from src.modules.chat.infrastructure.services import ws_manager
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================
class AgentQueueItem(BaseModel):
    id: str
    contact_id: str | None
    channel: str
    status: str
    priority: str
    last_message_at: str | None
    last_message_preview: str | None
    unread_count: int
    waiting_since: str | None
    escalation_reason: str | None


class AgentMetrics(BaseModel):
    active_conversations: int
    pending_conversations: int
    ai_handling: int
    agent_handling: int
    avg_response_time_seconds: float | None
    avg_resolution_time_seconds: float | None
    resolved_today: int
    messages_today: int


class AgentPerformance(BaseModel):
    agent_id: str
    agent_name: str
    active_conversations: int
    resolved_today: int
    avg_response_time: float | None
    satisfaction_avg: float | None
    is_online: bool


class SLAMetrics(BaseModel):
    total_conversations: int
    within_sla: int
    breached_sla: int
    sla_compliance_rate: float
    avg_first_response_seconds: float | None
    avg_resolution_seconds: float | None


class SatisfactionMetrics(BaseModel):
    total_ratings: int
    avg_score: float | None
    score_distribution: dict[str, int]  # {"1": 5, "2": 3, ...}
    positive_rate: float  # 4-5 stars


class OnlineAgent(BaseModel):
    user_id: str
    user_name: str
    connected_at: str


class SubmitCSATRequest(BaseModel):
    score: int  # 1-5
    comment: str | None = None


# =============================================================================
# Queue & Conversations
# =============================================================================

@router.get("/queue", summary="Get pending conversation queue")
async def get_queue(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Get unassigned conversations waiting for agent pickup."""
    stmt = (
        select(ConversationModel)
        .where(
            ConversationModel.tenant_id == current_user.tenant_id,
            ConversationModel.status == "pending",
            ConversationModel.assigned_agent_id.is_(None),
        )
        .order_by(
            case(
                (ConversationModel.priority == "urgent", 1),
                (ConversationModel.priority == "high", 2),
                (ConversationModel.priority == "normal", 3),
                else_=4,
            ),
            ConversationModel.last_message_at.asc(),
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    conversations = result.scalars().all()

    return {
        "data": [
            AgentQueueItem(
                id=str(c.id),
                contact_id=str(c.contact_id) if c.contact_id else None,
                channel=c.channel,
                status=c.status,
                priority=c.priority,
                last_message_at=c.last_message_at.isoformat() if c.last_message_at else None,
                last_message_preview=c.last_message_preview,
                unread_count=c.unread_count,
                waiting_since=c.created_at.isoformat() if c.created_at else None,
                escalation_reason=c.escalation_reason,
            ).model_dump()
            for c in conversations
        ],
        "total": len(conversations),
    }


# =============================================================================
# Metrics
# =============================================================================

@router.get("/metrics", summary="Get real-time agent panel metrics")
async def get_metrics(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentMetrics:
    """Get overview metrics for the agent panel."""
    tid = current_user.tenant_id
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Active conversations
    active_stmt = select(func.count(ConversationModel.id)).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.status == "active",
    )
    active = (await session.execute(active_stmt)).scalar_one()

    # Pending
    pending_stmt = select(func.count(ConversationModel.id)).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.status == "pending",
    )
    pending = (await session.execute(pending_stmt)).scalar_one()

    # AI handling vs Agent handling
    ai_stmt = select(func.count(ConversationModel.id)).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.status.in_(["active", "pending"]),
        ConversationModel.is_ai_handling.is_(True),
    )
    ai_count = (await session.execute(ai_stmt)).scalar_one()

    agent_stmt = select(func.count(ConversationModel.id)).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.status.in_(["active", "pending"]),
        ConversationModel.is_ai_handling.is_(False),
    )
    agent_count = (await session.execute(agent_stmt)).scalar_one()

    # Resolved today
    resolved_stmt = select(func.count(ConversationModel.id)).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.resolved_at >= today_start,
    )
    resolved = (await session.execute(resolved_stmt)).scalar_one()

    # Messages today
    messages_stmt = select(func.count(MessageModel.id)).where(
        MessageModel.tenant_id == tid,
        MessageModel.created_at >= today_start,
    )
    messages = (await session.execute(messages_stmt)).scalar_one()

    # Average response time (conversations with first_response_at)
    avg_resp_stmt = select(
        func.avg(
            extract("epoch", ConversationModel.first_response_at) -
            extract("epoch", ConversationModel.created_at)
        )
    ).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.first_response_at.isnot(None),
        ConversationModel.created_at >= today_start - timedelta(days=7),
    )
    avg_resp = (await session.execute(avg_resp_stmt)).scalar_one()

    # Average resolution time
    avg_res_stmt = select(
        func.avg(
            extract("epoch", ConversationModel.resolved_at) -
            extract("epoch", ConversationModel.created_at)
        )
    ).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.resolved_at.isnot(None),
        ConversationModel.resolved_at >= today_start - timedelta(days=7),
    )
    avg_res = (await session.execute(avg_res_stmt)).scalar_one()

    return AgentMetrics(
        active_conversations=active,
        pending_conversations=pending,
        ai_handling=ai_count,
        agent_handling=agent_count,
        avg_response_time_seconds=round(avg_resp, 1) if avg_resp else None,
        avg_resolution_time_seconds=round(avg_res, 1) if avg_res else None,
        resolved_today=resolved,
        messages_today=messages,
    )


# =============================================================================
# SLA
# =============================================================================

@router.get("/sla", summary="Get SLA compliance metrics")
async def get_sla_metrics(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=7, ge=1, le=90),
) -> SLAMetrics:
    """Get SLA compliance for the specified period."""
    tid = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)

    # Default SLA: first response within 5 minutes
    sla_threshold_seconds = 300  # 5 minutes

    # Total conversations in period
    total_stmt = select(func.count(ConversationModel.id)).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.created_at >= since,
        ConversationModel.first_response_at.isnot(None),
    )
    total = (await session.execute(total_stmt)).scalar_one()

    # Within SLA
    within_stmt = select(func.count(ConversationModel.id)).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.created_at >= since,
        ConversationModel.first_response_at.isnot(None),
        (extract("epoch", ConversationModel.first_response_at) -
         extract("epoch", ConversationModel.created_at)) <= sla_threshold_seconds,
    )
    within = (await session.execute(within_stmt)).scalar_one()

    breached = total - within
    compliance = (within / total * 100) if total > 0 else 100.0

    # Avg first response
    avg_first_stmt = select(
        func.avg(
            extract("epoch", ConversationModel.first_response_at) -
            extract("epoch", ConversationModel.created_at)
        )
    ).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.first_response_at.isnot(None),
        ConversationModel.created_at >= since,
    )
    avg_first = (await session.execute(avg_first_stmt)).scalar_one()

    # Avg resolution
    avg_res_stmt = select(
        func.avg(
            extract("epoch", ConversationModel.resolved_at) -
            extract("epoch", ConversationModel.created_at)
        )
    ).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.resolved_at.isnot(None),
        ConversationModel.created_at >= since,
    )
    avg_res = (await session.execute(avg_res_stmt)).scalar_one()

    return SLAMetrics(
        total_conversations=total,
        within_sla=within,
        breached_sla=breached,
        sla_compliance_rate=round(compliance, 1),
        avg_first_response_seconds=round(avg_first, 1) if avg_first else None,
        avg_resolution_seconds=round(avg_res, 1) if avg_res else None,
    )


# =============================================================================
# Satisfaction
# =============================================================================

@router.get("/satisfaction", summary="Get CSAT metrics")
async def get_satisfaction(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=30, ge=1, le=365),
) -> SatisfactionMetrics:
    """Get customer satisfaction metrics."""
    tid = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)

    # Get all rated conversations
    stmt = select(ConversationModel.csat_score).where(
        ConversationModel.tenant_id == tid,
        ConversationModel.csat_score.isnot(None),
        ConversationModel.created_at >= since,
    )
    result = await session.execute(stmt)
    scores = [row[0] for row in result.all()]

    total = len(scores)
    avg = sum(scores) / total if total > 0 else None

    # Distribution
    dist = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    positive = 0
    for s in scores:
        dist[str(s)] = dist.get(str(s), 0) + 1
        if s >= 4:
            positive += 1

    positive_rate = (positive / total) if total > 0 else 0.0

    return SatisfactionMetrics(
        total_ratings=total,
        avg_score=round(avg, 2) if avg else None,
        score_distribution=dist,
        positive_rate=round(positive_rate, 2),
    )


@router.post(
    "/conversations/{conversation_id}/csat",
    summary="Submit CSAT rating",
)
async def submit_csat(
    conversation_id: str,
    body: SubmitCSATRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Submit a satisfaction rating for a conversation (public, used by widget)."""
    if body.score < 1 or body.score > 5:
        from src.shared.api.exceptions import ValidationError_
        raise ValidationError_("Score must be between 1 and 5", "score")

    stmt = select(ConversationModel).where(ConversationModel.id == uuid.UUID(conversation_id))
    result = await session.execute(stmt)
    conv = result.scalar_one_or_none()
    if conv:
        conv.csat_score = body.score
        conv.csat_comment = body.comment
        await session.flush()

    return {"message": "Rating submitted"}


# =============================================================================
# Presence
# =============================================================================

@router.get("/online", summary="Get online agents")
async def get_online_agents(
    current_user: CurrentUser,
) -> dict:
    """Get list of currently online agents via WebSocket."""
    agents = ws_manager.get_online_agents(current_user.tenant_id)
    return {
        "data": [OnlineAgent(**a).model_dump() for a in agents],
        "total": len(agents),
    }


# =============================================================================
# Agent Performance
# =============================================================================

@router.get("/performance", summary="Get agent performance")
async def get_agent_performance(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=7, ge=1, le=90),
) -> dict:
    """Get performance metrics per agent."""
    tid = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)

    from src.modules.auth.infrastructure.models import UserModel

    # Get all agents with their conversation counts
    stmt = (
        select(
            UserModel.id,
            UserModel.full_name,
            func.count(ConversationModel.id).label("active"),
        )
        .outerjoin(
            ConversationModel,
            (ConversationModel.assigned_agent_id == UserModel.id) &
            (ConversationModel.status == "active"),
        )
        .where(
            UserModel.tenant_id == tid,
            UserModel.is_active.is_(True),
            UserModel.deleted_at.is_(None),
        )
        .group_by(UserModel.id, UserModel.full_name)
    )
    result = await session.execute(stmt)
    agents_data = result.all()

    performances = []
    for agent_id, agent_name, active_count in agents_data:
        # Resolved in period
        res_stmt = select(func.count(ConversationModel.id)).where(
            ConversationModel.assigned_agent_id == agent_id,
            ConversationModel.resolved_at >= since,
        )
        resolved = (await session.execute(res_stmt)).scalar_one()

        # Avg CSAT
        csat_stmt = select(func.avg(ConversationModel.csat_score)).where(
            ConversationModel.assigned_agent_id == agent_id,
            ConversationModel.csat_score.isnot(None),
            ConversationModel.created_at >= since,
        )
        avg_csat = (await session.execute(csat_stmt)).scalar_one()

        performances.append(
            AgentPerformance(
                agent_id=str(agent_id),
                agent_name=agent_name,
                active_conversations=active_count or 0,
                resolved_today=resolved,
                avg_response_time=None,  # Requires per-agent calculation
                satisfaction_avg=round(avg_csat, 2) if avg_csat else None,
                is_online=ws_manager.is_user_online(agent_id),
            ).model_dump()
        )

    return {"data": performances}
