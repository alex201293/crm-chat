"""
RBAC (Role-Based Access Control) service.
Manages roles, permissions, and their assignment to users.
Includes seed data for system roles and permissions.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.models import (
    PermissionModel,
    RoleModel,
    UserModel,
    role_permissions_table,
    user_roles_table,
)


# =============================================================================
# System Permissions Definition
# =============================================================================
SYSTEM_PERMISSIONS: list[dict[str, str]] = [
    # Auth
    {"code": "users:read", "name": "View users", "module": "auth"},
    {"code": "users:write", "name": "Create/edit users", "module": "auth"},
    {"code": "users:delete", "name": "Delete users", "module": "auth"},
    {"code": "roles:read", "name": "View roles", "module": "auth"},
    {"code": "roles:write", "name": "Create/edit roles", "module": "auth"},
    {"code": "tenant:settings", "name": "Manage tenant settings", "module": "auth"},
    # Chat
    {"code": "conversations:read", "name": "View conversations", "module": "chat"},
    {"code": "conversations:write", "name": "Send messages", "module": "chat"},
    {"code": "conversations:assign", "name": "Assign conversations", "module": "chat"},
    {"code": "conversations:close", "name": "Close conversations", "module": "chat"},
    # CRM
    {"code": "contacts:read", "name": "View contacts", "module": "crm"},
    {"code": "contacts:write", "name": "Create/edit contacts", "module": "crm"},
    {"code": "contacts:delete", "name": "Delete contacts", "module": "crm"},
    {"code": "deals:read", "name": "View deals", "module": "crm"},
    {"code": "deals:write", "name": "Create/edit deals", "module": "crm"},
    {"code": "deals:delete", "name": "Delete deals", "module": "crm"},
    {"code": "pipeline:manage", "name": "Manage pipeline stages", "module": "crm"},
    # Campaigns
    {"code": "campaigns:read", "name": "View campaigns", "module": "campaigns"},
    {"code": "campaigns:write", "name": "Create/edit campaigns", "module": "campaigns"},
    {"code": "campaigns:send", "name": "Send campaigns", "module": "campaigns"},
    {"code": "campaigns:delete", "name": "Delete campaigns", "module": "campaigns"},
    # Knowledge
    {"code": "knowledge:read", "name": "View knowledge base", "module": "knowledge"},
    {"code": "knowledge:write", "name": "Manage knowledge base", "module": "knowledge"},
    # Analytics
    {"code": "analytics:read", "name": "View analytics", "module": "analytics"},
    {"code": "analytics:export", "name": "Export analytics data", "module": "analytics"},
    # Channels
    {"code": "channels:read", "name": "View channel configs", "module": "channels"},
    {"code": "channels:write", "name": "Manage channel configs", "module": "channels"},
]

# =============================================================================
# System Roles with Default Permissions
# =============================================================================
SYSTEM_ROLES: dict[str, dict] = {
    "owner": {
        "display_name": "Owner",
        "description": "Full access to all features. Cannot be removed.",
        "permissions": [p["code"] for p in SYSTEM_PERMISSIONS],  # All permissions
    },
    "admin": {
        "display_name": "Administrator",
        "description": "Full access except tenant deletion and billing.",
        "permissions": [p["code"] for p in SYSTEM_PERMISSIONS],
    },
    "supervisor": {
        "display_name": "Supervisor",
        "description": "Manage agents and conversations, view analytics.",
        "permissions": [
            "users:read",
            "conversations:read",
            "conversations:write",
            "conversations:assign",
            "conversations:close",
            "contacts:read",
            "contacts:write",
            "deals:read",
            "deals:write",
            "campaigns:read",
            "campaigns:write",
            "campaigns:send",
            "knowledge:read",
            "analytics:read",
            "channels:read",
        ],
    },
    "agent": {
        "display_name": "Agent",
        "description": "Handle conversations and manage contacts.",
        "permissions": [
            "conversations:read",
            "conversations:write",
            "conversations:close",
            "contacts:read",
            "contacts:write",
            "deals:read",
            "deals:write",
            "knowledge:read",
            "analytics:read",
        ],
    },
    "viewer": {
        "display_name": "Viewer",
        "description": "Read-only access to conversations and contacts.",
        "permissions": [
            "conversations:read",
            "contacts:read",
            "deals:read",
            "campaigns:read",
            "analytics:read",
        ],
    },
}


class RBACService:
    """Service for managing roles and permissions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def seed_permissions(self) -> None:
        """Create system permissions if they don't exist."""
        for perm_data in SYSTEM_PERMISSIONS:
            stmt = select(PermissionModel).where(
                PermissionModel.code == perm_data["code"]
            )
            result = await self._session.execute(stmt)
            if not result.scalar_one_or_none():
                perm = PermissionModel(
                    code=perm_data["code"],
                    name=perm_data["name"],
                    module=perm_data["module"],
                )
                self._session.add(perm)

        await self._session.flush()

    async def seed_tenant_roles(self, tenant_id: uuid.UUID) -> None:
        """Create system roles for a new tenant."""
        # Get all permissions
        stmt = select(PermissionModel)
        result = await self._session.execute(stmt)
        all_permissions = {p.code: p for p in result.scalars().all()}

        for role_name, role_data in SYSTEM_ROLES.items():
            # Check if role already exists for this tenant
            stmt = select(RoleModel).where(
                RoleModel.name == role_name,
                RoleModel.tenant_id == tenant_id,
            )
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                role = RoleModel(
                    tenant_id=tenant_id,
                    name=role_name,
                    display_name=role_data["display_name"],
                    description=role_data["description"],
                    is_system=True,
                )
                self._session.add(role)
                await self._session.flush()

                # Assign permissions to role
                for perm_code in role_data["permissions"]:
                    if perm_code in all_permissions:
                        stmt = role_permissions_table.insert().values(
                            role_id=role.id,
                            permission_id=all_permissions[perm_code].id,
                        )
                        await self._session.execute(stmt)

        await self._session.flush()

    async def assign_role_to_user(
        self, user_id: uuid.UUID, role_name: str, tenant_id: uuid.UUID
    ) -> None:
        """Assign a role to a user within their tenant."""
        # Find the role
        stmt = select(RoleModel).where(
            RoleModel.name == role_name,
            RoleModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            raise ValueError(f"Role '{role_name}' not found for tenant")

        # Check if already assigned
        stmt = select(user_roles_table).where(
            user_roles_table.c.user_id == user_id,
            user_roles_table.c.role_id == role.id,
        )
        result = await self._session.execute(stmt)
        if result.first():
            return  # Already assigned

        # Assign
        stmt = user_roles_table.insert().values(user_id=user_id, role_id=role.id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def remove_role_from_user(
        self, user_id: uuid.UUID, role_name: str, tenant_id: uuid.UUID
    ) -> None:
        """Remove a role from a user."""
        stmt = select(RoleModel).where(
            RoleModel.name == role_name,
            RoleModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            return

        stmt = user_roles_table.delete().where(
            user_roles_table.c.user_id == user_id,
            user_roles_table.c.role_id == role.id,
        )
        await self._session.execute(stmt)

    async def get_user_permissions(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> set[str]:
        """Get all permissions for a user through their roles."""
        stmt = (
            select(PermissionModel.code)
            .join(role_permissions_table)
            .join(RoleModel)
            .join(user_roles_table)
            .where(
                user_roles_table.c.user_id == user_id,
                RoleModel.tenant_id == tenant_id,
            )
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_tenant_roles(self, tenant_id: uuid.UUID) -> list[dict]:
        """List all roles for a tenant with their permissions."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(RoleModel)
            .options(selectinload(RoleModel.permissions))
            .where(RoleModel.tenant_id == tenant_id)
            .order_by(RoleModel.name)
        )
        result = await self._session.execute(stmt)
        roles = result.scalars().all()

        return [
            {
                "id": str(role.id),
                "name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "is_system": role.is_system,
                "permissions": [p.code for p in role.permissions],
            }
            for role in roles
        ]
