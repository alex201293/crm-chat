"""Repository interfaces for the CRM bounded context."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.crm.domain.entities.activity import Activity
from src.modules.crm.domain.entities.company import Company
from src.modules.crm.domain.entities.contact import Contact
from src.modules.crm.domain.entities.deal import Deal
from src.modules.crm.domain.entities.note import Note
from src.modules.crm.domain.entities.pipeline import Pipeline
from src.modules.crm.domain.entities.task import Task
from src.modules.crm.domain.value_objects import (
    DealStatus,
    LifecycleStage,
    TaskStatus,
)


class IContactRepository(ABC):
    @abstractmethod
    async def create(self, contact: Contact) -> Contact: ...

    @abstractmethod
    async def get_by_id(
        self, contact_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Contact | None: ...

    @abstractmethod
    async def get_by_email(
        self, email: str, tenant_id: uuid.UUID
    ) -> Contact | None: ...

    @abstractmethod
    async def get_by_phone(
        self, phone: str, tenant_id: uuid.UUID
    ) -> Contact | None: ...

    @abstractmethod
    async def update(self, contact: Contact) -> Contact: ...

    @abstractmethod
    async def delete(
        self, contact_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        search: str | None = None,
        lifecycle_stage: LifecycleStage | None = None,
        tags: list[str] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Contact]: ...

    @abstractmethod
    async def count_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> int: ...


class ICompanyRepository(ABC):
    @abstractmethod
    async def create(self, company: Company) -> Company: ...

    @abstractmethod
    async def get_by_id(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Company | None: ...

    @abstractmethod
    async def update(self, company: Company) -> Company: ...

    @abstractmethod
    async def delete(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Company]: ...

    @abstractmethod
    async def count_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> int: ...


class IPipelineRepository(ABC):
    @abstractmethod
    async def create(self, pipeline: Pipeline) -> Pipeline: ...

    @abstractmethod
    async def get_by_id(
        self, pipeline_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Pipeline | None: ...

    @abstractmethod
    async def get_default(
        self, tenant_id: uuid.UUID
    ) -> Pipeline | None: ...

    @abstractmethod
    async def update(self, pipeline: Pipeline) -> Pipeline: ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[Pipeline]: ...


class IDealRepository(ABC):
    @abstractmethod
    async def create(self, deal: Deal) -> Deal: ...

    @abstractmethod
    async def get_by_id(
        self, deal_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Deal | None: ...

    @abstractmethod
    async def update(self, deal: Deal) -> Deal: ...

    @abstractmethod
    async def delete(
        self, deal_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None: ...

    @abstractmethod
    async def list_by_pipeline(
        self,
        pipeline_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: DealStatus | None = None,
        stage_id: uuid.UUID | None = None,
        assigned_to: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Deal]: ...

    @abstractmethod
    async def count_by_pipeline(
        self, pipeline_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int: ...

    @abstractmethod
    async def get_total_value(
        self,
        tenant_id: uuid.UUID,
        status: DealStatus | None = None,
    ) -> int: ...


class ITaskRepository(ABC):
    @abstractmethod
    async def create(self, task: Task) -> Task: ...

    @abstractmethod
    async def get_by_id(
        self, task_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Task | None: ...

    @abstractmethod
    async def update(self, task: Task) -> Task: ...

    @abstractmethod
    async def delete(
        self, task_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        assigned_to: uuid.UUID | None = None,
        status: TaskStatus | None = None,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]: ...


class INoteRepository(ABC):
    @abstractmethod
    async def create(self, note: Note) -> Note: ...

    @abstractmethod
    async def update(self, note: Note) -> Note: ...

    @abstractmethod
    async def delete(
        self, note_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None: ...

    @abstractmethod
    async def list_by_contact(
        self,
        contact_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Note]: ...

    @abstractmethod
    async def list_by_deal(
        self,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Note]: ...


class IActivityRepository(ABC):
    @abstractmethod
    async def create(self, activity: Activity) -> Activity: ...

    @abstractmethod
    async def list_by_contact(
        self,
        contact_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 30,
    ) -> list[Activity]: ...

    @abstractmethod
    async def list_by_deal(
        self,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 30,
    ) -> list[Activity]: ...
