"""Note entity for the CRM module."""

import uuid
from datetime import datetime

from src.shared.domain.base_entity import BaseEntity


class Note(BaseEntity):
    """Internal note attached to a contact or deal."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
        author_id: uuid.UUID | None = None,
        content: str = "",
        is_pinned: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.contact_id = contact_id
        self.deal_id = deal_id
        self.author_id = author_id
        self.content = content
        self.is_pinned = is_pinned
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
        contact_id: uuid.UUID | None = None,
        deal_id: uuid.UUID | None = None,
    ) -> "Note":
        return cls(
            tenant_id=tenant_id,
            author_id=author_id,
            content=content.strip(),
            contact_id=contact_id,
            deal_id=deal_id,
        )

    def pin(self) -> None:
        self.is_pinned = True
        self.updated_at = datetime.utcnow()

    def unpin(self) -> None:
        self.is_pinned = False
        self.updated_at = datetime.utcnow()
