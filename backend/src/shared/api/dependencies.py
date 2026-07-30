"""
Shared FastAPI dependencies.
Provides common dependency injection for routes.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.api.exceptions import AuthenticationError, TenantNotFoundError
from src.shared.infrastructure.database.session import get_db_session


async def get_current_tenant_id(request: Request) -> uuid.UUID:
    """
    Dependency that extracts and validates the tenant ID from request context.
    Raises TenantNotFoundError if no tenant can be resolved.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise TenantNotFoundError()
    try:
        return uuid.UUID(tenant_id)
    except (ValueError, AttributeError) as e:
        raise TenantNotFoundError() from e


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
TenantId = Annotated[uuid.UUID, Depends(get_current_tenant_id)]
