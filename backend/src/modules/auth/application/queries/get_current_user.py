"""
Use case: Get the current authenticated user's profile.
"""

import uuid
from dataclasses import dataclass

from src.modules.auth.domain.interfaces.user_repository import IUserRepository
from src.shared.api.exceptions import EntityNotFoundError


@dataclass
class CurrentUserDTO:
    """User profile data returned to the client."""

    id: str
    tenant_id: str
    email: str
    full_name: str
    avatar_url: str | None
    phone: str | None
    is_verified: bool
    mfa_enabled: bool
    roles: list[str]
    permissions: list[str]
    tenant_name: str | None
    created_at: str


class GetCurrentUserHandler:
    """Retrieves the authenticated user's profile."""

    def __init__(self, user_repository: IUserRepository) -> None:
        self._user_repo = user_repository

    async def execute(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CurrentUserDTO:
        user = await self._user_repo.get_by_id(user_id, tenant_id)
        if not user:
            raise EntityNotFoundError("User", str(user_id))

        # Get tenant name
        tenant_name: str | None = None
        if hasattr(self._user_repo, "_session"):
            from sqlalchemy import select
            from src.modules.auth.infrastructure.models import TenantModel

            session = self._user_repo._session  # type: ignore[attr-defined]
            stmt = select(TenantModel.name).where(TenantModel.id == tenant_id)
            result = await session.execute(stmt)
            tenant_name = result.scalar_one_or_none()

        return CurrentUserDTO(
            id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=str(user.email),
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            roles=user.roles,
            permissions=sorted(user.permissions),
            tenant_name=tenant_name,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )
