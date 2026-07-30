"""Use cases for Deal management and pipeline transitions."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.modules.crm.domain.entities.activity import Activity
from src.modules.crm.domain.entities.deal import Deal
from src.modules.crm.domain.interfaces.repositories import (
    IActivityRepository,
    IDealRepository,
    IPipelineRepository,
)
from src.modules.crm.domain.value_objects import ActivityType
from src.shared.api.exceptions import EntityNotFoundError, ValidationError_
from src.shared.domain.events import event_bus


@dataclass
class CreateDealCommand:
    tenant_id: uuid.UUID
    title: str
    pipeline_id: uuid.UUID | None = None  # None = use default
    stage_id: uuid.UUID | None = None  # None = first stage
    value: int = 0  # In cents
    currency: str = "USD"
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    assigned_to_id: uuid.UUID | None = None
    expected_close_date: datetime | None = None


class CreateDealHandler:
    def __init__(
        self,
        deal_repo: IDealRepository,
        pipeline_repo: IPipelineRepository,
        activity_repo: IActivityRepository,
    ) -> None:
        self._deal_repo = deal_repo
        self._pipeline_repo = pipeline_repo
        self._activity_repo = activity_repo

    async def execute(self, cmd: CreateDealCommand) -> Deal:
        if not cmd.title.strip():
            raise ValidationError_("Title is required", "title")

        # Resolve pipeline
        if cmd.pipeline_id:
            pipeline = await self._pipeline_repo.get_by_id(
                cmd.pipeline_id, cmd.tenant_id
            )
        else:
            pipeline = await self._pipeline_repo.get_default(cmd.tenant_id)

        if not pipeline:
            raise EntityNotFoundError("Pipeline", "default")

        # Resolve stage
        stage_id = cmd.stage_id
        if not stage_id:
            first_stage = pipeline.active_stages[0] if pipeline.active_stages else None
            if not first_stage:
                raise ValidationError_("Pipeline has no active stages")
            stage_id = first_stage.id

        # Determine probability from stage
        stage = pipeline.get_stage_by_id(stage_id)
        probability = stage.probability if stage else 0

        deal = Deal.create(
            tenant_id=cmd.tenant_id,
            pipeline_id=pipeline.id,
            stage_id=stage_id,
            title=cmd.title,
            value=cmd.value,
            currency=cmd.currency,
            contact_id=cmd.contact_id,
            company_id=cmd.company_id,
            assigned_to_id=cmd.assigned_to_id,
            expected_close_date=cmd.expected_close_date,
        )
        deal.probability = probability

        await self._deal_repo.create(deal)

        # Activity
        activity = Activity.create(
            tenant_id=cmd.tenant_id,
            activity_type=ActivityType.NOTE,
            title=f"Deal created: {deal.title}",
            deal_id=deal.id,
            contact_id=cmd.contact_id,
        )
        await self._activity_repo.create(activity)

        return deal


@dataclass
class MoveDealStageCommand:
    tenant_id: uuid.UUID
    deal_id: uuid.UUID
    new_stage_id: uuid.UUID


class MoveDealStageHandler:
    def __init__(
        self,
        deal_repo: IDealRepository,
        pipeline_repo: IPipelineRepository,
        activity_repo: IActivityRepository,
    ) -> None:
        self._deal_repo = deal_repo
        self._pipeline_repo = pipeline_repo
        self._activity_repo = activity_repo

    async def execute(self, cmd: MoveDealStageCommand) -> Deal:
        deal = await self._deal_repo.get_by_id(cmd.deal_id, cmd.tenant_id)
        if not deal:
            raise EntityNotFoundError("Deal", str(cmd.deal_id))

        pipeline = await self._pipeline_repo.get_by_id(
            deal.pipeline_id, cmd.tenant_id
        )
        if not pipeline:
            raise EntityNotFoundError("Pipeline", str(deal.pipeline_id))

        new_stage = pipeline.get_stage_by_id(cmd.new_stage_id)
        if not new_stage:
            raise EntityNotFoundError("Stage", str(cmd.new_stage_id))

        # Handle terminal stages
        if new_stage.is_won:
            deal.mark_won()
        elif new_stage.is_lost:
            deal.mark_lost()
        else:
            deal.move_to_stage(cmd.new_stage_id, new_stage.probability)

        await self._deal_repo.update(deal)

        # Activity
        activity = Activity.create(
            tenant_id=cmd.tenant_id,
            activity_type=ActivityType.DEAL_STAGE_CHANGED,
            title=f"Deal moved to: {new_stage.name}",
            deal_id=deal.id,
            contact_id=deal.contact_id,
            metadata={"stage_name": new_stage.name},
        )
        await self._activity_repo.create(activity)

        # Publish events
        await event_bus.publish_all(deal.clear_domain_events())
        return deal


@dataclass
class WinDealCommand:
    tenant_id: uuid.UUID
    deal_id: uuid.UUID


class WinDealHandler:
    def __init__(
        self,
        deal_repo: IDealRepository,
        activity_repo: IActivityRepository,
    ) -> None:
        self._deal_repo = deal_repo
        self._activity_repo = activity_repo

    async def execute(self, cmd: WinDealCommand) -> Deal:
        deal = await self._deal_repo.get_by_id(cmd.deal_id, cmd.tenant_id)
        if not deal:
            raise EntityNotFoundError("Deal", str(cmd.deal_id))

        deal.mark_won()
        await self._deal_repo.update(deal)

        activity = Activity.create(
            tenant_id=cmd.tenant_id,
            activity_type=ActivityType.DEAL_WON,
            title=f"Deal won: {deal.title} ({deal.value_display} {deal.currency})",
            deal_id=deal.id,
            contact_id=deal.contact_id,
        )
        await self._activity_repo.create(activity)
        await event_bus.publish_all(deal.clear_domain_events())
        return deal


@dataclass
class LoseDealCommand:
    tenant_id: uuid.UUID
    deal_id: uuid.UUID
    reason: str | None = None


class LoseDealHandler:
    def __init__(
        self,
        deal_repo: IDealRepository,
        activity_repo: IActivityRepository,
    ) -> None:
        self._deal_repo = deal_repo
        self._activity_repo = activity_repo

    async def execute(self, cmd: LoseDealCommand) -> Deal:
        deal = await self._deal_repo.get_by_id(cmd.deal_id, cmd.tenant_id)
        if not deal:
            raise EntityNotFoundError("Deal", str(cmd.deal_id))

        deal.mark_lost(cmd.reason)
        await self._deal_repo.update(deal)

        activity = Activity.create(
            tenant_id=cmd.tenant_id,
            activity_type=ActivityType.DEAL_LOST,
            title=f"Deal lost: {deal.title}",
            deal_id=deal.id,
            contact_id=deal.contact_id,
            metadata={"reason": cmd.reason} if cmd.reason else None,
        )
        await self._activity_repo.create(activity)
        await event_bus.publish_all(deal.clear_domain_events())
        return deal
