"""
SQLAlchemy ORM models for the Auth module.
Includes: Tenant, User, Role, Permission, RefreshToken, AuditLog.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.infrastructure.database.base import Base, SoftDeleteMixin, TimestampMixin


# =============================================================================
# Tenant (Organization / Company)
# =============================================================================
class TenantModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Represents a company/organization in the multi-tenant system.
    Top-level entity that owns all data.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_conversations_per_month: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000
    )

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(back_populates="tenant", lazy="selectin")


# =============================================================================
# Association tables
# =============================================================================
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


# =============================================================================
# User
# =============================================================================
class UserModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Application user belonging to a tenant.
    Can have multiple roles with granular permissions.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
        Index("ix_users_tenant_email", "tenant_id", "email"),
        Index("ix_users_tenant_active", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # OAuth fields
    google_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    microsoft_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    tenant: Mapped["TenantModel"] = relationship(back_populates="users")
    roles: Mapped[list["RoleModel"]] = relationship(
        secondary=user_roles_table, back_populates="users", lazy="selectin"
    )
    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# =============================================================================
# Role
# =============================================================================
class RoleModel(Base, TimestampMixin):
    """
    Role definition with associated permissions.
    System roles (owner, admin, agent) are not deletable.
    """

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("name", "tenant_id", name="uq_role_name_tenant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(
        secondary=user_roles_table, back_populates="roles"
    )
    permissions: Mapped[list["PermissionModel"]] = relationship(
        secondary=role_permissions_table, back_populates="roles", lazy="selectin"
    )


# =============================================================================
# Permission
# =============================================================================
class PermissionModel(Base):
    """
    Granular permission definition.
    Format: resource:action (e.g., conversations:read, campaigns:create)
    """

    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    roles: Mapped[list["RoleModel"]] = relationship(
        secondary=role_permissions_table, back_populates="permissions"
    )


# =============================================================================
# Refresh Token
# =============================================================================
class RefreshTokenModel(Base, TimestampMixin):
    """
    Refresh token for JWT token rotation.
    Stored per device/session for revocation support.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_active", "user_id", "is_revoked"),
        Index("ix_refresh_tokens_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    device_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="refresh_tokens")


# =============================================================================
# Audit Log
# =============================================================================
class AuditLogModel(Base):
    """
    Immutable audit trail for sensitive actions.
    Partitioned by created_at for performance at scale.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
