"""
Database seeding for permissions and initial data.
Run with: python -m src.modules.auth.infrastructure.services.seed
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.services.rbac_service import RBACService
from src.shared.infrastructure.database.session import async_session_factory


async def seed_permissions() -> None:
    """Seed all system permissions into the database."""
    async with async_session_factory() as session:
        rbac = RBACService(session)
        await rbac.seed_permissions()
        await session.commit()
        print("Permissions seeded successfully.")


async def seed_tenant_roles(tenant_id_str: str) -> None:
    """Seed system roles for a specific tenant."""
    import uuid

    tenant_id = uuid.UUID(tenant_id_str)
    async with async_session_factory() as session:
        rbac = RBACService(session)
        await rbac.seed_permissions()
        await rbac.seed_tenant_roles(tenant_id)
        await session.commit()
        print(f"Roles seeded for tenant {tenant_id}")


if __name__ == "__main__":
    asyncio.run(seed_permissions())
