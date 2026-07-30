"""Use cases for Task management."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.modules.crm.domain.entities.activity import Activity
from src.modules.crm.domain.entities.task import Task
from src.modules.crm.domain.interfaces.repositories import (
    IActivityRepository,
    ITaskRepository,
)
from src.modules.crm.domain.value_objects import ActivityType, TaskPriority
from src.shared.api.exceptions import EntityNotFoundError, ValidationError_


@dataclass
class CreateTaskCommand:
    tenant_id: uuid.UUID
    title: str
    assigned_to_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    deal_id: uuid.UUID | None = None
    description: str | None = None
    due_date: datetime | None = None
    priority: str = "normal"


class CreateTaskHandler:
    def __init__(self, task_repo: ITaskRepository) -> None:
        self._task_repo = task_repo

    async def execute(self, cmd: CreateTaskCommand) -> Task:
        if not cmd.title.strip():
            raise ValidationError_("Title is required", "title")

        task = Task.create(
            tenant_id=cmd.tenant_id,
            title=cmd.title,
            assigned_to_id=cmd.assigned_to_id,
            contact_id=cmd.contact_id,
            deal_id=cmd.deal_id,
            due_date=cmd.due_date,
            priority=TaskPriority(cmd.priority),
        )
        task.description = cmd.description

        await self._task_repo.create(task)
        return task


@dataclass
class CompleteTaskCommand:
    tenant_id: uuid.UUID
    task_id: uuid.UUID


class CompleteTaskHandler:
    def __init__(
        self,
        task_repo: ITaskRepository,
        activity_repo: IActivityRepository,
    ) -> None:
        self._task_repo = task_repo
        self._activity_repo = activity_repo

    async def execute(self, cmd: CompleteTaskCommand) -> Task:
        task = await self._task_repo.get_by_id(cmd.task_id, cmd.tenant_id)
        if not task:
            raise EntityNotFoundError("Task", str(cmd.task_id))

        task.complete()
        await self._task_repo.update(task)

        # Record activity
        activity = Activity.create(
            tenant_id=cmd.tenant_id,
            activity_type=ActivityType.TASK_COMPLETED,
            title=f"Task completed: {task.title}",
            contact_id=task.contact_id,
            deal_id=task.deal_id,
        )
        await self._activity_repo.create(activity)

        return task
