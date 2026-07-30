"""
Dashboard API endpoints.
Provides analytics and metrics for the main dashboard:
conversations, AI vs humans, deals, campaigns, agents, revenue.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case, extract, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.modules.auth.api.dependencies import CurrentUser
from src.modules.chat.infrastructure.models import ConversationModel, MessageModel
from src.modules.crm.infrastructure.models import (
    ContactModel,
    DealModel,
)
from src.modules.campaigns.infrastructure.repositories import CampaignModel
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================
class OverviewMetrics(BaseModel):
    total_conversations: int
    active_conversations: int
    total_contacts: int
    total_deals_value: int  # cents
    deals_won_value: int
    open_deals_count: int
    ai_handled_percent: float
    avg_response_time_seconds: float | None
    avg_satisfaction: float | None
    campaigns_sent: int


class TimeSeriesPoint(BaseModel):
    date: str
    value: int


class ConversationAnalytics(BaseModel):
    total: int
    by_channel: dict[str, int]
    by_status: dict[str, int]
    ai_vs_human: dict[str, int]
    daily_trend: list[TimeSeriesPoint]


class DealAnalytics(BaseModel):
    total_open: int
    total_won: int
    total_lost: int
    pipeline_value: int  # cents, open deals
    won_value: int
    won_this_month: int
    lost_this_month: int
    avg_deal_size: int  # cents
    conversion_rate: float


class CampaignAnalytics(BaseModel):
    total_campaigns: int
    completed: int
    total_sent: int
    total_delivered: int
    total_read: int
    total_clicked: int
    avg_delivery_rate: float
    avg_open_rate: float
    by_channel: dict[str, int]


class AgentProductivity(BaseModel):
    total_agents: int
    online_now: int
    avg_conversations_per_agent: float
    avg_resolution_time_seconds: float | None
    top_agents: list[dict]


# =============================================================================
# Overview
# =============================================================================

@router.get("/overview", summary="Dashboard overview")
async def get_overview(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OverviewMetrics:
    """Main dashboard overview with key metrics."""
    tid = current_user.tenant_id

    # Total conversations
    total_conv = (await session.execute(
        select(func.count(ConversationModel.id)).where(ConversationModel.tenant_id == tid)
    )).scalar_one()

    # Active
    active_conv = (await session.execute(
        select(func.count(ConversationModel.id)).where(
            ConversationModel.tenant_id == tid,
            ConversationModel.status.in_(["active", "pending"]),
        )
    )).scalar_one()

    # Contacts
    total_contacts = (await session.execute(
        select(func.count(ContactModel.id)).where(
            ContactModel.tenant_id == tid, ContactModel.deleted_at.is_(None)
        )
    )).scalar_one()

    # Deals value
    total_deals = (await session.execute(
        select(func.coalesce(func.sum(DealModel.value), 0)).where(
            DealModel.tenant_id == tid, DealModel.deleted_at.is_(None),
            DealModel.won_at.is_(None), DealModel.lost_at.is_(None),
        )
    )).scalar_one()

    won_value = (await session.execute(
        select(func.coalesce(func.sum(DealModel.value), 0)).where(
            DealModel.tenant_id == tid, DealModel.won_at.isnot(None),
        )
    )).scalar_one()

    open_deals = (await session.execute(
        select(func.count(DealModel.id)).where(
            DealModel.tenant_id == tid, DealModel.deleted_at.is_(None),
            DealModel.won_at.is_(None), DealModel.lost_at.is_(None),
        )
    )).scalar_one()

    # AI handled percent
    ai_count = (await session.execute(
        select(func.count(ConversationModel.id)).where(
            ConversationModel.tenant_id == tid,
            ConversationModel.is_ai_handling.is_(True),
            ConversationModel.status.in_(["active", "pending"]),
        )
    )).scalar_one()
    ai_pct = (ai_count / active_conv * 100) if active_conv > 0 else 0.0

    # Avg response time (last 30 days)
    avg_resp = (await session.execute(
        select(func.avg(
            extract("epoch", ConversationModel.first_response_at) -
            extract("epoch", ConversationModel.created_at)
        )).where(
            ConversationModel.tenant_id == tid,
            ConversationModel.first_response_at.isnot(None),
            ConversationModel.created_at >= datetime.utcnow() - timedelta(days=30),
        )
    )).scalar_one()

    # Avg satisfaction
    avg_csat = (await session.execute(
        select(func.avg(ConversationModel.csat_score)).where(
            ConversationModel.tenant_id == tid,
            ConversationModel.csat_score.isnot(None),
        )
    )).scalar_one()

    # Campaigns sent
    campaigns_sent = (await session.execute(
        select(func.count(CampaignModel.id)).where(
            CampaignModel.tenant_id == tid,
            CampaignModel.status == "completed",
        )
    )).scalar_one()

    return OverviewMetrics(
        total_conversations=total_conv,
        active_conversations=active_conv,
        total_contacts=total_contacts,
        total_deals_value=total_deals,
        deals_won_value=won_value,
        open_deals_count=open_deals,
        ai_handled_percent=round(ai_pct, 1),
        avg_response_time_seconds=round(avg_resp, 1) if avg_resp else None,
        avg_satisfaction=round(avg_csat, 2) if avg_csat else None,
        campaigns_sent=campaigns_sent,
    )


# =============================================================================
# Conversations Analytics
# =============================================================================

@router.get("/conversations", summary="Conversation analytics")
async def get_conversation_analytics(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=30, ge=1, le=365),
) -> ConversationAnalytics:
    """Detailed conversation analytics with trends."""
    tid = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)

    total = (await session.execute(
        select(func.count(ConversationModel.id)).where(
            ConversationModel.tenant_id == tid,
            ConversationModel.created_at >= since,
        )
    )).scalar_one()

    # By channel
    channel_stmt = (
        select(ConversationModel.channel, func.count(ConversationModel.id))
        .where(ConversationModel.tenant_id == tid, ConversationModel.created_at >= since)
        .group_by(ConversationModel.channel)
    )
    channel_result = await session.execute(channel_stmt)
    by_channel = {row[0]: row[1] for row in channel_result.all()}

    # By status
    status_stmt = (
        select(ConversationModel.status, func.count(ConversationModel.id))
        .where(ConversationModel.tenant_id == tid)
        .group_by(ConversationModel.status)
    )
    status_result = await session.execute(status_stmt)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # AI vs Human
    ai = (await session.execute(
        select(func.count(ConversationModel.id)).where(
            ConversationModel.tenant_id == tid,
            ConversationModel.is_ai_handling.is_(True),
            ConversationModel.created_at >= since,
        )
    )).scalar_one()
    ai_vs_human = {"ai": ai, "human": total - ai}

    # Daily trend (last N days)
    daily_stmt = (
        select(
            func.date_trunc("day", ConversationModel.created_at).label("day"),
            func.count(ConversationModel.id),
        )
        .where(ConversationModel.tenant_id == tid, ConversationModel.created_at >= since)
        .group_by(text("day"))
        .order_by(text("day"))
    )
    daily_result = await session.execute(daily_stmt)
    daily_trend = [
        TimeSeriesPoint(date=row[0].strftime("%Y-%m-%d"), value=row[1])
        for row in daily_result.all()
    ]

    return ConversationAnalytics(
        total=total, by_channel=by_channel, by_status=by_status,
        ai_vs_human=ai_vs_human, daily_trend=daily_trend,
    )


# =============================================================================
# Deals Analytics
# =============================================================================

@router.get("/deals", summary="Deal analytics")
async def get_deal_analytics(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DealAnalytics:
    """Pipeline and deal performance metrics."""
    tid = current_user.tenant_id
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

    open_count = (await session.execute(
        select(func.count(DealModel.id)).where(
            DealModel.tenant_id == tid, DealModel.deleted_at.is_(None),
            DealModel.won_at.is_(None), DealModel.lost_at.is_(None),
        )
    )).scalar_one()

    won_count = (await session.execute(
        select(func.count(DealModel.id)).where(
            DealModel.tenant_id == tid, DealModel.won_at.isnot(None),
        )
    )).scalar_one()

    lost_count = (await session.execute(
        select(func.count(DealModel.id)).where(
            DealModel.tenant_id == tid, DealModel.lost_at.isnot(None),
        )
    )).scalar_one()

    pipeline_value = (await session.execute(
        select(func.coalesce(func.sum(DealModel.value), 0)).where(
            DealModel.tenant_id == tid, DealModel.deleted_at.is_(None),
            DealModel.won_at.is_(None), DealModel.lost_at.is_(None),
        )
    )).scalar_one()

    won_value = (await session.execute(
        select(func.coalesce(func.sum(DealModel.value), 0)).where(
            DealModel.tenant_id == tid, DealModel.won_at.isnot(None),
        )
    )).scalar_one()

    won_month = (await session.execute(
        select(func.count(DealModel.id)).where(
            DealModel.tenant_id == tid, DealModel.won_at >= month_start,
        )
    )).scalar_one()

    lost_month = (await session.execute(
        select(func.count(DealModel.id)).where(
            DealModel.tenant_id == tid, DealModel.lost_at >= month_start,
        )
    )).scalar_one()

    avg_size = (await session.execute(
        select(func.coalesce(func.avg(DealModel.value), 0)).where(
            DealModel.tenant_id == tid, DealModel.won_at.isnot(None),
        )
    )).scalar_one()

    total_closed = won_count + lost_count
    conv_rate = (won_count / total_closed) if total_closed > 0 else 0.0

    return DealAnalytics(
        total_open=open_count, total_won=won_count, total_lost=lost_count,
        pipeline_value=pipeline_value, won_value=won_value,
        won_this_month=won_month, lost_this_month=lost_month,
        avg_deal_size=int(avg_size),
        conversion_rate=round(conv_rate, 2),
    )


# =============================================================================
# Campaigns Analytics
# =============================================================================

@router.get("/campaigns", summary="Campaign analytics")
async def get_campaign_analytics(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignAnalytics:
    """Aggregate campaign performance metrics."""
    tid = current_user.tenant_id

    total = (await session.execute(
        select(func.count(CampaignModel.id)).where(CampaignModel.tenant_id == tid)
    )).scalar_one()

    completed = (await session.execute(
        select(func.count(CampaignModel.id)).where(
            CampaignModel.tenant_id == tid, CampaignModel.status == "completed"
        )
    )).scalar_one()

    # Aggregate metrics
    agg_stmt = select(
        func.coalesce(func.sum(CampaignModel.sent_count), 0),
        func.coalesce(func.sum(CampaignModel.delivered_count), 0),
        func.coalesce(func.sum(CampaignModel.read_count), 0),
        func.coalesce(func.sum(CampaignModel.clicked_count), 0),
    ).where(CampaignModel.tenant_id == tid)
    agg = (await session.execute(agg_stmt)).one()
    sent, delivered, read, clicked = agg

    avg_delivery = (delivered / sent) if sent > 0 else 0.0
    avg_open = (read / delivered) if delivered > 0 else 0.0

    # By channel
    ch_stmt = (
        select(CampaignModel.channel, func.count(CampaignModel.id))
        .where(CampaignModel.tenant_id == tid)
        .group_by(CampaignModel.channel)
    )
    ch_result = await session.execute(ch_stmt)
    by_channel = {row[0]: row[1] for row in ch_result.all()}

    return CampaignAnalytics(
        total_campaigns=total, completed=completed,
        total_sent=sent, total_delivered=delivered,
        total_read=read, total_clicked=clicked,
        avg_delivery_rate=round(avg_delivery, 3),
        avg_open_rate=round(avg_open, 3),
        by_channel=by_channel,
    )


# =============================================================================
# Agent Productivity
# =============================================================================

@router.get("/agents", summary="Agent productivity analytics")
async def get_agent_productivity(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentProductivity:
    """Aggregate agent productivity metrics."""
    tid = current_user.tenant_id
    from src.modules.auth.infrastructure.models import UserModel
    from src.modules.chat.infrastructure.services import ws_manager

    # Total agents
    total_agents = (await session.execute(
        select(func.count(UserModel.id)).where(
            UserModel.tenant_id == tid,
            UserModel.is_active.is_(True),
            UserModel.deleted_at.is_(None),
        )
    )).scalar_one()

    online = len(ws_manager.get_online_agents(tid))

    # Avg conversations per agent
    agent_conv_stmt = (
        select(func.count(ConversationModel.id))
        .where(
            ConversationModel.tenant_id == tid,
            ConversationModel.assigned_agent_id.isnot(None),
            ConversationModel.status == "active",
        )
    )
    total_assigned = (await session.execute(agent_conv_stmt)).scalar_one()
    avg_per_agent = (total_assigned / total_agents) if total_agents > 0 else 0.0

    # Avg resolution time
    avg_res = (await session.execute(
        select(func.avg(
            extract("epoch", ConversationModel.resolved_at) -
            extract("epoch", ConversationModel.created_at)
        )).where(
            ConversationModel.tenant_id == tid,
            ConversationModel.resolved_at.isnot(None),
            ConversationModel.resolved_at >= datetime.utcnow() - timedelta(days=30),
        )
    )).scalar_one()

    # Top 5 agents by resolved count
    top_stmt = (
        select(
            UserModel.id, UserModel.full_name,
            func.count(ConversationModel.id).label("resolved"),
        )
        .join(ConversationModel, ConversationModel.assigned_agent_id == UserModel.id)
        .where(
            UserModel.tenant_id == tid,
            ConversationModel.resolved_at.isnot(None),
            ConversationModel.resolved_at >= datetime.utcnow() - timedelta(days=30),
        )
        .group_by(UserModel.id, UserModel.full_name)
        .order_by(text("resolved DESC"))
        .limit(5)
    )
    top_result = await session.execute(top_stmt)
    top_agents = [
        {"agent_id": str(r[0]), "name": r[1], "resolved": r[2]}
        for r in top_result.all()
    ]

    return AgentProductivity(
        total_agents=total_agents,
        online_now=online,
        avg_conversations_per_agent=round(avg_per_agent, 1),
        avg_resolution_time_seconds=round(avg_res, 1) if avg_res else None,
        top_agents=top_agents,
    )
