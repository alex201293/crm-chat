"""Repository interfaces for the Campaigns module."""

import uuid
from abc import ABC, abstractmethod

from src.modules.campaigns.domain.entities import (
    Campaign,
    CampaignMessage,
    Segment,
)
from src.modules.campaigns.domain.value_objects import CampaignStatus


class ICampaignRepository(ABC):
    @abstractmethod
    async def create(self, campaign: Campaign) -> Campaign: ...

    @abstractmethod
    async def get_by_id(
        self, campaign_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Campaign | None: ...

    @abstractmethod
    async def update(self, campaign: Campaign) -> Campaign: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: CampaignStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Campaign]: ...

    @abstractmethod
    async def count_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> int: ...

    @abstractmethod
    async def get_scheduled_ready(self) -> list[Campaign]:
        """Get campaigns that are scheduled and ready to send."""
        ...


class ISegmentRepository(ABC):
    @abstractmethod
    async def create(self, segment: Segment) -> Segment: ...

    @abstractmethod
    async def get_by_id(
        self, segment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Segment | None: ...

    @abstractmethod
    async def update(self, segment: Segment) -> Segment: ...

    @abstractmethod
    async def delete(
        self, segment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None: ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[Segment]: ...

    @abstractmethod
    async def get_contact_ids(
        self, segment_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Evaluate segment filters and return matching contact IDs."""
        ...


class ICampaignMessageRepository(ABC):
    @abstractmethod
    async def create(self, message: CampaignMessage) -> CampaignMessage: ...

    @abstractmethod
    async def create_batch(
        self, messages: list[CampaignMessage]
    ) -> None: ...

    @abstractmethod
    async def update_status(
        self, message_id: uuid.UUID, **kwargs
    ) -> None: ...

    @abstractmethod
    async def get_pending_for_campaign(
        self, campaign_id: uuid.UUID, limit: int = 100
    ) -> list[CampaignMessage]: ...

    @abstractmethod
    async def count_by_status(
        self, campaign_id: uuid.UUID
    ) -> dict[str, int]: ...
