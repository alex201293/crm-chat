"""Repository interface for User aggregate."""

import uuid
from abc import ABC, abstractmethod

from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.value_objects.email import Email


class IUserRepository(ABC):
    """
    Port for user persistence.
    Implementation lives in infrastructure layer.
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persist a new user."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User | None:
        """Find a user by ID within a tenant."""
        ...

    @abstractmethod
    async def get_by_email(self, email: Email, tenant_id: uuid.UUID) -> User | None:
        """Find a user by email within a tenant."""
        ...

    @abstractmethod
    async def get_by_email_any_tenant(self, email: Email) -> User | None:
        """Find a user by email across all tenants (for login)."""
        ...

    @abstractmethod
    async def get_by_google_id(self, google_id: str) -> User | None:
        """Find a user by Google OAuth ID."""
        ...

    @abstractmethod
    async def get_by_microsoft_id(self, microsoft_id: str) -> User | None:
        """Find a user by Microsoft OAuth ID."""
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user."""
        ...

    @abstractmethod
    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        """Count active users in a tenant."""
        ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> list[User]:
        """List users for a tenant with pagination."""
        ...
