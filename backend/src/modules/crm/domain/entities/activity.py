"""Activity entity for CRM timeline."""

import uuid
from datetime import datetime

from src.modules.crm.domain.value_objects import ActivityType
from src.shared.domain.base_entity import BaseEntity


class Activity(BaseEntity):
    """Timeline activity for contacts and deals."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        activity_type: ActivityType = ActivityType.NOTE,
        title: str = "",
        description: str | None = None,
        metadata: dict | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(
            id=id, tenant_id=tenant_id, created_at=created_at
        )
        self.contact_id = contact_id
        self.deal_id = deal_id
        self.user_id = user_id
        self.activity_type = activity_type
        self.title = title
        self.description = description
        self.metadata = metadata or {}

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        activity_type: ActivityType,
        title: str,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> "Activity":
        return cls(
            tenant_id=tenant_id,
            contact_id=contact_id,
            deal_id=deal_id,
            user_id=user_id,
            activity_type=activity_type,
            title=title,
            description=description,
            metadata=metadata,
        )
