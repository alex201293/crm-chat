"""
Role management endpoints.
Only accessible by owners and admins.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.api.dependencies import CurrentUser, require_roles
from src.modules.auth.infrastructure.services.rbac_service import RBACService
from src.shared.api.exceptions import AuthorizationError
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


class RoleResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str | None
    is_system: bool
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    user_id: str
    role_name: str


class RolesListResponse(BaseModel):
    roles: list[RoleResponse]


@router.get(
    "/roles",
    response_model=RolesListResponse,
    summary="List all roles for the tenant",
)
async def list_roles(
    current_user: Annotated[CurrentUser, Depends(require_roles("owner", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RolesListResponse:
    """Get all roles available in the current tenant."""
    rbac = RBACService(session)
    roles = await rbac.get_tenant_roles(current_user.tenant_id)
    return RolesListResponse(
        roles=[RoleResponse(**role) for role in roles]
    )


@router.post(
    "/roles/assign",
    response_model=dict,
    summary="Assign a role to a user",
)
async def assign_role(
    body: AssignRoleRequest,
    current_user: Annotated[CurrentUser, Depends(require_roles("owner", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Assign a role to a user. Only owners can assign the owner role."""
    # Only owners can assign owner role
    if body.role_name == "owner" and not current_user.has_role("owner"):
        raise AuthorizationError("Only owners can assign the owner role")

    rbac = RBACService(session)
    await rbac.assign_role_to_user(
        user_id=uuid.UUID(body.user_id),
        role_name=body.role_name,
        tenant_id=current_user.tenant_id,
    )
    return {"message": f"Role '{body.role_name}' assigned successfully"}


@router.post(
    "/roles/revoke",
    response_model=dict,
    summary="Remove a role from a user",
)
async def revoke_role(
    body: AssignRoleRequest,
    current_user: Annotated[CurrentUser, Depends(require_roles("owner", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Remove a role from a user. Cannot remove the last owner."""
    if body.role_name == "owner" and not current_user.has_role("owner"):
        raise AuthorizationError("Only owners can revoke the owner role")

    # Prevent removing own owner role
    if body.role_name == "owner" and str(current_user.id) == body.user_id:
        raise AuthorizationError("Cannot remove your own owner role")

    rbac = RBACService(session)
    await rbac.remove_role_from_user(
        user_id=uuid.UUID(body.user_id),
        role_name=body.role_name,
        tenant_id=current_user.tenant_id,
    )
    return {"message": f"Role '{body.role_name}' revoked successfully"}


@router.get(
    "/permissions",
    response_model=dict,
    summary="List all available permissions",
)
async def list_permissions(
    current_user: Annotated[CurrentUser, Depends(require_roles("owner", "admin"))],
) -> dict:
    """Get all system permissions grouped by module."""
    from src.modules.auth.infrastructure.services.rbac_service import SYSTEM_PERMISSIONS

    grouped: dict[str, list[dict]] = {}
    for perm in SYSTEM_PERMISSIONS:
        module = perm["module"]
        if module not in grouped:
            grouped[module] = []
        grouped[module].append({"code": perm["code"], "name": perm["name"]})

    return {"permissions": grouped}
