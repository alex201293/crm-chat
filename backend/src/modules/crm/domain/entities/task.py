"""Task entity for the CRM module."""

import uuid
from datetime import datetime

from src.modules.crm.domain.value_objects import TaskPriority, TaskStatus
from src.shared.domain.base_entity import BaseEntity


class Task(BaseEntity):
    """A task related to a contact or deal."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
        assigned_to_id: uuid.UUID | None = None,
        title: str = "",
        description: str | None = None,
        status: TaskStatus = TaskStatus.PENDING,
        priority: TaskPriority = TaskPriority.NORMAL,
        due_date: datetime | None = None,
        completed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.contact_id = contact_id
        self.deal_id = deal_id
        self.assigned_to_id = assigned_to_id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.due_date = due_date
        self.completed_at = completed_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        title: str,
        assigned_to_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
        due_date: datetime | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> "Task":
        return cls(
            tenant_id=tenant_id,
            title=title.strip(),
            assigned_to_id=assigned_to_id,
            contact_id=contact_id,
            deal_id=deal_id,
            due_date=due_date,
            priority=priority,
        )

    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def start(self) -> None:
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return False
        return datetime.utcnow() > self.due_date
