"""
FastAPI dependencies for authentication and authorization.
Provides current user injection and permission checking.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.interfaces.token_service import TokenPayload
from src.modules.auth.infrastructure.repositories.user_repository import UserRepository
from src.modules.auth.infrastructure.services.jwt_token_service import JWTTokenService
from src.shared.api.exceptions import AuthenticationError, AuthorizationError
from src.shared.infrastructure.database.session import get_db_session

# HTTP Bearer scheme for OpenAPI docs
security_scheme = HTTPBearer(auto_error=False)


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenPayload:
    """
    Extract and validate the JWT access token from the Authorization header.
    Returns the decoded token payload.
    """
    if not credentials:
        raise AuthenticationError("Missing authentication token")

    token_service = JWTTokenService(session)
    return token_service.decode_access_token(credentials.credentials)


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Resolve the full User entity from the token payload.
    Includes roles and permissions.
    """
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(payload.user_id, payload.tenant_id)

    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the user is active. Alias for clarity in route signatures."""
    return user


def require_permissions(*permissions: str):
    """
    Dependency factory that checks if the current user has ALL required permissions.
    Usage: Depends(require_permissions("conversations:read", "contacts:write"))
    """

    async def permission_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        for permission in permissions:
            if not user.has_permission(permission):
                raise AuthorizationError(
                    f"Missing required permission: {permission}"
                )
        return user

    return permission_checker


def require_any_permission(*permissions: str):
    """
    Dependency factory that checks if the current user has ANY of the required permissions.
    """

    async def permission_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not user.has_any_permission(list(permissions)):
            raise AuthorizationError(
                f"Requires one of: {', '.join(permissions)}"
            )
        return user

    return permission_checker


def require_roles(*roles: str):
    """
    Dependency factory that checks if the current user has ANY of the required roles.
    Usage: Depends(require_roles("owner", "admin"))
    """

    async def role_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not any(user.has_role(role) for role in roles):
            raise AuthorizationError(
                f"Requires one of roles: {', '.join(roles)}"
            )
        return user

    return role_checker


# Type aliases for use in route signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
TokenData = Annotated[TokenPayload, Depends(get_token_payload)]
