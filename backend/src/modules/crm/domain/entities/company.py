"""Company entity for the CRM module."""

import uuid
from datetime import datetime

from src.shared.domain.base_entity import AggregateRoot


class Company(AggregateRoot):
    """A business entity that contacts belong to."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        name: str = "",
        domain: str | None = None,
        industry: str | None = None,
        size: str | None = None,
        website: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        country: str | None = None,
        annual_revenue: int | None = None,
        custom_fields: dict | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.name = name
        self.domain = domain
        self.industry = industry
        self.size = size
        self.website = website
        self.phone = phone
        self.address = address
        self.country = country
        self.annual_revenue = annual_revenue
        self.custom_fields = custom_fields or {}

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        name: str,
        domain: str | None = None,
        industry: str | None = None,
    ) -> "Company":
        return cls(
            tenant_id=tenant_id,
            name=name.strip(),
            domain=domain,
            industry=industry,
        )
