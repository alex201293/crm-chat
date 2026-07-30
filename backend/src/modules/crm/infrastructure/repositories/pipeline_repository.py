"""SQLAlchemy implementation of IPipelineRepository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.crm.domain.entities.pipeline import Pipeline, PipelineStage
from src.modules.crm.domain.interfaces.repositories import IPipelineRepository
from src.modules.crm.infrastructure.models import PipelineModel, PipelineStageModel


class PipelineRepository(IPipelineRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, pipeline: Pipeline) -> Pipeline:
        model = PipelineModel(
            id=pipeline.id,
            tenant_id=pipeline.tenant_id,
            name=pipeline.name,
            is_default=pipeline.is_default,
            is_active=pipeline.is_active,
        )
        self._session.add(model)
        await self._session.flush()

        # Create stages
        for stage in pipeline.stages:
            stage_model = PipelineStageModel(
                id=stage.id,
                tenant_id=pipeline.tenant_id,
                pipeline_id=pipeline.id,
                name=stage.name,
                color=stage.color,
                order=stage.order,
                is_won=stage.is_won,
                is_lost=stage.is_lost,
                probability=stage.probability,
            )
            self._session.add(stage_model)

        await self._session.flush()
        return pipeline

    async def get_by_id(
        self, pipeline_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Pipeline | None:
        stmt = (
            select(PipelineModel)
            .options(selectinload(PipelineModel.stages))
            .where(
                PipelineModel.id == pipeline_id,
                PipelineModel.tenant_id == tenant_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_default(self, tenant_id: uuid.UUID) -> Pipeline | None:
        stmt = (
            select(PipelineModel)
            .options(selectinload(PipelineModel.stages))
            .where(
                PipelineModel.tenant_id == tenant_id,
                PipelineModel.is_default.is_(True),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, pipeline: Pipeline) -> Pipeline:
        stmt = select(PipelineModel).where(PipelineModel.id == pipeline.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Pipeline {pipeline.id} not found")

        model.name = pipeline.name
        model.is_default = pipeline.is_default
        model.is_active = pipeline.is_active
        await self._session.flush()
        return pipeline

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Pipeline]:
        stmt = (
            select(PipelineModel)
            .options(selectinload(PipelineModel.stages))
            .where(PipelineModel.tenant_id == tenant_id)
            .order_by(PipelineModel.is_default.desc(), PipelineModel.name)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: PipelineModel) -> Pipeline:
        stages = [
            PipelineStage(
                id=s.id,
                tenant_id=s.tenant_id,
                pipeline_id=s.pipeline_id,
                name=s.name,
                color=s.color,
                order=s.order,
                is_won=s.is_won,
                is_lost=s.is_lost,
                probability=s.probability,
            )
            for s in sorted(model.stages, key=lambda x: x.order)
        ]

        return Pipeline(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            is_default=model.is_default,
            is_active=model.is_active,
            stages=stages,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
