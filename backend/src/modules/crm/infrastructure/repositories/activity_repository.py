"""SQLAlchemy implementation of IActivityRepository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities.activity import Activity
from src.modules.crm.domain.interfaces.repositories import IActivityRepository
from src.modules.crm.domain.value_objects import ActivityType
from src.modules.crm.infrastructure.models import ActivityModel


class ActivityRepository(IActivityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, activity: Activity) -> Activity:
        model = ActivityModel(
            id=activity.id,
            tenant_id=activity.tenant_id,
            contact_id=activity.contact_id,
            deal_id=activity.deal_id,
            user_id=activity.user_id,
            activity_type=activity.activity_type.value,
            title=activity.title,
            description=activity.description,
            metadata_=activity.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return activity

    async def list_by_contact(
        self,
        contact_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 30,
    ) -> list[Activity]:
        stmt = (
            select(ActivityModel)
            .where(
                ActivityModel.contact_id == contact_id,
                ActivityModel.tenant_id == tenant_id,
            )
            .order_by(ActivityModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_deal(
        self,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 30,
    ) -> list[Activity]:
        stmt = (
            select(ActivityModel)
            .where(
                ActivityModel.deal_id == deal_id,
                ActivityModel.tenant_id == tenant_id,
            )
            .order_by(ActivityModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: ActivityModel) -> Activity:
        return Activity(
            id=model.id,
            tenant_id=model.tenant_id,
            contact_id=model.contact_id,
            deal_id=model.deal_id,
            user_id=model.user_id,
            activity_type=ActivityType(model.activity_type),
            title=model.title,
            description=model.description,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
        )
