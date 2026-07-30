"""Use cases for Pipeline management."""

import uuid
from dataclasses import dataclass

from src.modules.crm.domain.entities.pipeline import Pipeline
from src.modules.crm.domain.interfaces.repositories import IPipelineRepository


@dataclass
class CreateDefaultPipelineCommand:
    tenant_id: uuid.UUID


class CreateDefaultPipelineHandler:
    """Creates the default pipeline for a new tenant."""

    def __init__(self, pipeline_repo: IPipelineRepository) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(self, cmd: CreateDefaultPipelineCommand) -> Pipeline:
        # Check if default already exists
        existing = await self._pipeline_repo.get_default(cmd.tenant_id)
        if existing:
            return existing

        pipeline = Pipeline.create_default(cmd.tenant_id)
        await self._pipeline_repo.create(pipeline)
        return pipeline
