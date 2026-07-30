"""
Tenant aggregate root.
Represents an organization/company in the multi-tenant system.
"""

import uuid
from datetime import datetime

from src.shared.domain.base_entity import AggregateRoot


class Tenant(AggregateRoot):
    """Organization that owns all data within its scope."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        name: str = "",
        slug: str = "",
        domain: str | None = None,
        logo_url: str | None = None,
        plan: str = "free",
        settings: dict | None = None,
        is_active: bool = True,
        max_users: int = 5,
        max_conversations_per_month: int = 1000,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.name = name
        self.slug = slug
        self.domain = domain
        self.logo_url = logo_url
        self.plan = plan
        self.settings = settings or {}
        self.is_active = is_active
        self.max_users = max_users
        self.max_conversations_per_month = max_conversations_per_month

    @classmethod
    def create(cls, name: str, slug: str) -> "Tenant":
        """Factory method for creating a new tenant with default settings."""
        return cls(
            name=name,
            slug=slug,
            settings={
                "ai_provider": "openai",
                "ai_model": "gpt-4o",
                "language": "es",
                "timezone": "America/Mexico_City",
                "widget_color": "#3B82F6",
                "widget_position": "bottom-right",
            },
        )

    def can_add_user(self, current_user_count: int) -> bool:
        """Check if the tenant can add more users based on plan limits."""
        return current_user_count < self.max_users

    def upgrade_plan(self, plan: str, max_users: int, max_conversations: int) -> None:
        """Upgrade the tenant's plan."""
        self.plan = plan
        self.max_users = max_users
        self.max_conversations_per_month = max_conversations
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the tenant."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
