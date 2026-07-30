"""Query handlers for CRM data retrieval."""

import uuid
from dataclasses import dataclass

from src.modules.crm.domain.entities.contact import Contact
from src.modules.crm.domain.entities.deal import Deal
from src.modules.crm.domain.entities.pipeline import Pipeline
from src.modules.crm.domain.interfaces.repositories import (
    IContactRepository,
    IDealRepository,
    IPipelineRepository,
)
from src.modules.crm.domain.value_objects import DealStatus, LifecycleStage


@dataclass
class GetContactsQuery:
    tenant_id: uuid.UUID
    search: str | None = None
    lifecycle_stage: str | None = None
    tags: list[str] | None = None
    page: int = 1
    page_size: int = 20


class GetContactsHandler:
    def __init__(self, contact_repo: IContactRepository) -> None:
        self._contact_repo = contact_repo

    async def execute(self, query: GetContactsQuery) -> tuple[list[Contact], int]:
        stage = LifecycleStage(query.lifecycle_stage) if query.lifecycle_stage else None
        offset = (query.page - 1) * query.page_size

        contacts = await self._contact_repo.list_by_tenant(
            tenant_id=query.tenant_id,
            search=query.search,
            lifecycle_stage=stage,
            tags=query.tags,
            offset=offset,
            limit=query.page_size,
        )
        total = await self._contact_repo.count_by_tenant(query.tenant_id)
        return contacts, total


@dataclass
class GetDealsQuery:
    tenant_id: uuid.UUID
    pipeline_id: uuid.UUID
    status: str | None = None
    stage_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    page: int = 1
    page_size: int = 50


class GetDealsHandler:
    def __init__(self, deal_repo: IDealRepository) -> None:
        self._deal_repo = deal_repo

    async def execute(self, query: GetDealsQuery) -> tuple[list[Deal], int]:
        status = DealStatus(query.status) if query.status else None
        offset = (query.page - 1) * query.page_size

        deals = await self._deal_repo.list_by_pipeline(
            pipeline_id=query.pipeline_id,
            tenant_id=query.tenant_id,
            status=status,
            stage_id=query.stage_id,
            assigned_to=query.assigned_to,
            offset=offset,
            limit=query.page_size,
        )
        total = await self._deal_repo.count_by_pipeline(
            query.pipeline_id, query.tenant_id
        )
        return deals, total


@dataclass
class GetPipelineQuery:
    tenant_id: uuid.UUID
    pipeline_id: uuid.UUID | None = None  # None = get default


class GetPipelineHandler:
    def __init__(self, pipeline_repo: IPipelineRepository) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(self, query: GetPipelineQuery) -> Pipeline | None:
        if query.pipeline_id:
            return await self._pipeline_repo.get_by_id(
                query.pipeline_id, query.tenant_id
            )
        return await self._pipeline_repo.get_default(query.tenant_id)
