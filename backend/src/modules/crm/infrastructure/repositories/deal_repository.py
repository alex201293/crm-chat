"""SQLAlchemy implementation of IDealRepository."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities.deal import Deal
from src.modules.crm.domain.interfaces.repositories import IDealRepository
from src.modules.crm.domain.value_objects import DealStatus
from src.modules.crm.infrastructure.models import DealModel


class DealRepository(IDealRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, deal: Deal) -> Deal:
        model = DealModel(
            id=deal.id,
            tenant_id=deal.tenant_id,
            pipeline_id=deal.pipeline_id,
            stage_id=deal.stage_id,
            contact_id=deal.contact_id,
            company_id=deal.company_id,
            assigned_to_id=deal.assigned_to_id,
            title=deal.title,
            value=deal.value,
            currency=deal.currency,
            probability=deal.probability,
            expected_close_date=deal.expected_close_date,
            tags=deal.tags,
            custom_fields=deal.custom_fields,
        )
        self._session.add(model)
        await self._session.flush()
        return deal

    async def get_by_id(
        self, deal_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Deal | None:
        stmt = select(DealModel).where(
            DealModel.id == deal_id,
            DealModel.tenant_id == tenant_id,
            DealModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, deal: Deal) -> Deal:
        stmt = select(DealModel).where(DealModel.id == deal.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Deal {deal.id} not found")

        model.stage_id = deal.stage_id
        model.contact_id = deal.contact_id
        model.company_id = deal.company_id
        model.assigned_to_id = deal.assigned_to_id
        model.title = deal.title
        model.value = deal.value
        model.currency = deal.currency
        model.probability = deal.probability
        model.expected_close_date = deal.expected_close_date
        model.won_at = deal.won_at
        model.lost_at = deal.lost_at
        model.lost_reason = deal.lost_reason
        model.tags = deal.tags
        model.custom_fields = deal.custom_fields
        await self._session.flush()
        return deal

    async def delete(
        self, deal_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        stmt = select(DealModel).where(
            DealModel.id == deal_id,
            DealModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.deleted_at = datetime.utcnow()
            await self._session.flush()

    async def list_by_pipeline(
        self,
        pipeline_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: DealStatus | None = None,
        stage_id: uuid.UUID | None = None,
        assigned_to: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Deal]:
        stmt = select(DealModel).where(
            DealModel.pipeline_id == pipeline_id,
            DealModel.tenant_id == tenant_id,
            DealModel.deleted_at.is_(None),
        )
        if status:
            if status == DealStatus.OPEN:
                stmt = stmt.where(
                    DealModel.won_at.is_(None),
                    DealModel.lost_at.is_(None),
                )
            elif status == DealStatus.WON:
                stmt = stmt.where(DealModel.won_at.isnot(None))
            elif status == DealStatus.LOST:
                stmt = stmt.where(DealModel.lost_at.isnot(None))
        if stage_id:
            stmt = stmt.where(DealModel.stage_id == stage_id)
        if assigned_to:
            stmt = stmt.where(DealModel.assigned_to_id == assigned_to)

        stmt = (
            stmt.order_by(DealModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_pipeline(
        self, pipeline_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        stmt = select(func.count(DealModel.id)).where(
            DealModel.pipeline_id == pipeline_id,
            DealModel.tenant_id == tenant_id,
            DealModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_total_value(
        self,
        tenant_id: uuid.UUID,
        status: DealStatus | None = None,
    ) -> int:
        stmt = select(func.coalesce(func.sum(DealModel.value), 0)).where(
            DealModel.tenant_id == tenant_id,
            DealModel.deleted_at.is_(None),
        )
        if status == DealStatus.WON:
            stmt = stmt.where(DealModel.won_at.isnot(None))
        elif status == DealStatus.OPEN:
            stmt = stmt.where(
                DealModel.won_at.is_(None), DealModel.lost_at.is_(None)
            )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _to_entity(self, model: DealModel) -> Deal:
        status = DealStatus.OPEN
        if model.won_at:
            status = DealStatus.WON
        elif model.lost_at:
            status = DealStatus.LOST

        return Deal(
            id=model.id,
            tenant_id=model.tenant_id,
            pipeline_id=model.pipeline_id,
            stage_id=model.stage_id,
            contact_id=model.contact_id,
            company_id=model.company_id,
            assigned_to_id=model.assigned_to_id,
            title=model.title,
            value=model.value,
            currency=model.currency,
            probability=model.probability,
            expected_close_date=model.expected_close_date,
            status=status,
            won_at=model.won_at,
            lost_at=model.lost_at,
            lost_reason=model.lost_reason,
            tags=model.tags or [],
            custom_fields=model.custom_fields or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
