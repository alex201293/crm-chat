"""SQLAlchemy implementation of IUserRepository."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.interfaces.user_repository import IUserRepository
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.password import HashedPassword
from src.modules.auth.infrastructure.models import (
    RoleModel,
    UserModel,
)


class UserRepository(IUserRepository):
    """PostgreSQL user repository via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            tenant_id=user.tenant_id,
            email=str(user.email),
            password_hash=user.password_hash.value if user.password_hash else "",
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            mfa_secret=user.mfa_secret,
            google_id=user.google_id,
            microsoft_id=user.microsoft_id,
            preferences={},
        )
        self._session.add(model)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User | None:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
            .where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_email(self, email: Email, tenant_id: uuid.UUID) -> User | None:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
            .where(
                UserModel.email == str(email),
                UserModel.tenant_id == tenant_id,
                UserModel.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_email_any_tenant(self, email: Email) -> User | None:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
            .where(
                UserModel.email == str(email),
                UserModel.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_google_id(self, google_id: str) -> User | None:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
            .where(UserModel.google_id == google_id, UserModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_microsoft_id(self, microsoft_id: str) -> User | None:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
            .where(UserModel.microsoft_id == microsoft_id, UserModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def update(self, user: User) -> User:
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"User {user.id} not found for update")

        model.email = str(user.email)
        model.password_hash = user.password_hash.value if user.password_hash else model.password_hash
        model.full_name = user.full_name
        model.avatar_url = user.avatar_url
        model.phone = user.phone
        model.is_active = user.is_active
        model.is_verified = user.is_verified
        model.mfa_enabled = user.mfa_enabled
        model.mfa_secret = user.mfa_secret
        model.last_login_at = user.last_login_at
        model.last_login_ip = user.last_login_ip
        model.google_id = user.google_id
        model.microsoft_id = user.microsoft_id

        await self._session.flush()
        return user

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count(UserModel.id)).where(
            UserModel.tenant_id == tenant_id,
            UserModel.is_active.is_(True),
            UserModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> list[User]:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.roles))
            .where(UserModel.tenant_id == tenant_id, UserModel.deleted_at.is_(None))
            .order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: UserModel) -> User:
        """Map ORM model to domain entity."""
        roles = [r.name for r in model.roles] if model.roles else []
        permissions: set[str] = set()
        if model.roles:
            for role in model.roles:
                if role.permissions:
                    for perm in role.permissions:
                        permissions.add(perm.code)

        return User(
            id=model.id,
            tenant_id=model.tenant_id,
            email=Email(model.email),
            password_hash=HashedPassword(model.password_hash),
            full_name=model.full_name,
            avatar_url=model.avatar_url,
            phone=model.phone,
            is_active=model.is_active,
            is_verified=model.is_verified,
            mfa_enabled=model.mfa_enabled,
            mfa_secret=model.mfa_secret,
            roles=roles,
            permissions=permissions,
            last_login_at=model.last_login_at,
            last_login_ip=model.last_login_ip,
            google_id=model.google_id,
            microsoft_id=model.microsoft_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
