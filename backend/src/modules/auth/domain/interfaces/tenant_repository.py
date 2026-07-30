"""Repository interface for Tenant aggregate."""

import uuid
from abc import ABC, abstractmethod

from src.modules.auth.domain.entities.tenant import Tenant


class ITenantRepository(ABC):
    """Port for tenant persistence."""

    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        """Persist a new tenant."""
        ...

    @abstractmethod
    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Find a tenant by ID."""
        ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Find a tenant by slug."""
        ...

    @abstractmethod
    async def get_by_domain(self, domain: str) -> Tenant | None:
        """Find a tenant by custom domain."""
        ...

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """Update an existing tenant."""
        ...

    @abstractmethod
    async def slug_exists(self, slug: str) -> bool:
        """Check if a slug is already in use."""
        ...
