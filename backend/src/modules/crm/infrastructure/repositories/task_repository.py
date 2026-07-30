"""SQLAlchemy implementation of ITaskRepository."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities.task import Task
from src.modules.crm.domain.interfaces.repositories import ITaskRepository
from src.modules.crm.domain.value_objects import TaskPriority, TaskStatus
from src.modules.crm.infrastructure.models import TaskModel


class TaskRepository(ITaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task: Task) -> Task:
        model = TaskModel(
            id=task.id,
            tenant_id=task.tenant_id,
            contact_id=task.contact_id,
            deal_id=task.deal_id,
            assigned_to_id=task.assigned_to_id,
            title=task.title,
            description=task.description,
            status=task.status.value,
            priority=task.priority.value,
            due_date=task.due_date,
            completed_at=task.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return task

    async def get_by_id(
        self, task_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Task | None:
        stmt = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, task: Task) -> Task:
        stmt = select(TaskModel).where(TaskModel.id == task.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Task {task.id} not found")

        model.title = task.title
        model.description = task.description
        model.status = task.status.value
        model.priority = task.priority.value
        model.due_date = task.due_date
        model.completed_at = task.completed_at
        model.assigned_to_id = task.assigned_to_id
        await self._session.flush()
        return task

    async def delete(
        self, task_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        from sqlalchemy import delete as sa_delete

        stmt = sa_delete(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.tenant_id == tenant_id,
        )
        await self._session.execute(stmt)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        assigned_to: uuid.UUID | None = None,
        status: TaskStatus | None = None,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.tenant_id == tenant_id
        )
        if assigned_to:
            stmt = stmt.where(TaskModel.assigned_to_id == assigned_to)
        if status:
            stmt = stmt.where(TaskModel.status == status.value)
        if contact_id:
            stmt = stmt.where(TaskModel.contact_id == contact_id)
        if deal_id:
            stmt = stmt.where(TaskModel.deal_id == deal_id)

        stmt = (
            stmt.order_by(TaskModel.due_date.asc().nullslast())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: TaskModel) -> Task:
        return Task(
            id=model.id,
            tenant_id=model.tenant_id,
            contact_id=model.contact_id,
            deal_id=model.deal_id,
            assigned_to_id=model.assigned_to_id,
            title=model.title,
            description=model.description,
            status=TaskStatus(model.status),
            priority=TaskPriority(model.priority),
            due_date=model.due_date,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
