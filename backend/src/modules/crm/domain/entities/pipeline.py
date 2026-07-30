"""Pipeline and Stage entities for the CRM module."""

import uuid
from datetime import datetime
from dataclasses import dataclass, field

from src.shared.domain.base_entity import AggregateRoot, BaseEntity


class PipelineStage(BaseEntity):
    """A stage within a pipeline."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        pipeline_id: uuid.UUID | None = None,
        name: str = "",
        color: str = "#3B82F6",
        order: int = 0,
        is_won: bool = False,
        is_lost: bool = False,
        probability: int = 0,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.pipeline_id = pipeline_id
        self.name = name
        self.color = color
        self.order = order
        self.is_won = is_won
        self.is_lost = is_lost
        self.probability = probability


class Pipeline(AggregateRoot):
    """
    Sales pipeline with ordered stages.
    Each tenant can have multiple pipelines.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        name: str = "",
        is_default: bool = False,
        is_active: bool = True,
        stages: list[PipelineStage] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.name = name
        self.is_default = is_default
        self.is_active = is_active
        self.stages = stages or []

    @classmethod
    def create_default(cls, tenant_id: uuid.UUID) -> "Pipeline":
        """Create the default sales pipeline with standard stages."""
        pipeline = cls(
            tenant_id=tenant_id,
            name="Sales Pipeline",
            is_default=True,
            is_active=True,
        )

        default_stages = [
            ("New Lead", "#94A3B8", 0, False, False, 10),
            ("Contacted", "#3B82F6", 1, False, False, 20),
            ("Qualified", "#8B5CF6", 2, False, False, 40),
            ("Proposal", "#F59E0B", 3, False, False, 60),
            ("Negotiation", "#F97316", 4, False, False, 80),
            ("Won", "#10B981", 5, True, False, 100),
            ("Lost", "#EF4444", 6, False, True, 0),
        ]

        for name, color, order, is_won, is_lost, probability in default_stages:
            stage = PipelineStage(
                tenant_id=tenant_id,
                pipeline_id=pipeline.id,
                name=name,
                color=color,
                order=order,
                is_won=is_won,
                is_lost=is_lost,
                probability=probability,
            )
            pipeline.stages.append(stage)

        return pipeline

    def add_stage(self, name: str, color: str = "#3B82F6", probability: int = 0) -> PipelineStage:
        """Add a new stage at the end (before won/lost)."""
        # Find position before terminal stages
        non_terminal = [s for s in self.stages if not s.is_won and not s.is_lost]
        order = len(non_terminal)

        stage = PipelineStage(
            tenant_id=self.tenant_id,
            pipeline_id=self.id,
            name=name,
            color=color,
            order=order,
            probability=probability,
        )
        self.stages.append(stage)
        self._reorder_stages()
        self.updated_at = datetime.utcnow()
        return stage

    def remove_stage(self, stage_id: uuid.UUID) -> None:
        """Remove a stage (cannot remove won/lost)."""
        self.stages = [s for s in self.stages if s.id != stage_id]
        self._reorder_stages()
        self.updated_at = datetime.utcnow()

    def reorder_stages(self, stage_ids: list[uuid.UUID]) -> None:
        """Reorder stages by providing the desired order of IDs."""
        stage_map = {s.id: s for s in self.stages}
        reordered = []
        for i, sid in enumerate(stage_ids):
            if sid in stage_map:
                stage_map[sid].order = i
                reordered.append(stage_map[sid])
        self.stages = reordered
        self.updated_at = datetime.utcnow()

    def _reorder_stages(self) -> None:
        """Ensure stages have sequential order values."""
        sorted_stages = sorted(self.stages, key=lambda s: (s.is_won or s.is_lost, s.order))
        for i, stage in enumerate(sorted_stages):
            stage.order = i
        self.stages = sorted_stages

    def get_stage_by_id(self, stage_id: uuid.UUID) -> PipelineStage | None:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        return None

    @property
    def active_stages(self) -> list[PipelineStage]:
        """Stages that are not terminal (won/lost)."""
        return [s for s in self.stages if not s.is_won and not s.is_lost]

    @property
    def won_stage(self) -> PipelineStage | None:
        return next((s for s in self.stages if s.is_won), None)

    @property
    def lost_stage(self) -> PipelineStage | None:
        return next((s for s in self.stages if s.is_lost), None)
