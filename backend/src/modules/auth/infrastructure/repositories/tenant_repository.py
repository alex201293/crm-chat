"""SQLAlchemy implementation of ITenantRepository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.domain.entities.tenant import Tenant
from src.modules.auth.domain.interfaces.tenant_repository import ITenantRepository
from src.modules.auth.infrastructure.models import TenantModel


class TenantRepository(ITenantRepository):
    """PostgreSQL tenant repository via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant: Tenant) -> Tenant:
        model = TenantModel(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            logo_url=tenant.logo_url,
            plan=tenant.plan,
            settings=tenant.settings,
            is_active=tenant.is_active,
            max_users=tenant.max_users,
            max_conversations_per_month=tenant.max_conversations_per_month,
        )
        self._session.add(model)
        await self._session.flush()
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        stmt = select(TenantModel).where(
            TenantModel.id == tenant_id,
            TenantModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(TenantModel).where(
            TenantModel.slug == slug,
            TenantModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_domain(self, domain: str) -> Tenant | None:
        stmt = select(TenantModel).where(
            TenantModel.domain == domain,
            TenantModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def update(self, tenant: Tenant) -> Tenant:
        stmt = select(TenantModel).where(TenantModel.id == tenant.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Tenant {tenant.id} not found for update")

        model.name = tenant.name
        model.slug = tenant.slug
        model.domain = tenant.domain
        model.logo_url = tenant.logo_url
        model.plan = tenant.plan
        model.settings = tenant.settings
        model.is_active = tenant.is_active
        model.max_users = tenant.max_users
        model.max_conversations_per_month = tenant.max_conversations_per_month

        await self._session.flush()
        return tenant

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(TenantModel.id).where(TenantModel.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _to_entity(self, model: TenantModel) -> Tenant:
        return Tenant(
            id=model.id,
            name=model.name,
            slug=model.slug,
            domain=model.domain,
            logo_url=model.logo_url,
            plan=model.plan,
            settings=model.settings,
            is_active=model.is_active,
            max_users=model.max_users,
            max_conversations_per_month=model.max_conversations_per_month,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
