"""
User aggregate root.
Encapsulates user identity, authentication state, and role assignments.
"""

import uuid
from datetime import datetime

from src.modules.auth.domain.events.auth_events import (
    MFAEnabled,
    PasswordChanged,
    UserLoggedIn,
    UserRegistered,
)
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.password import HashedPassword
from src.shared.domain.base_entity import AggregateRoot


class User(AggregateRoot):
    """User aggregate root with authentication capabilities."""

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        email: Email | None = None,
        password_hash: HashedPassword | None = None,
        full_name: str = "",
        avatar_url: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
        is_verified: bool = False,
        mfa_enabled: bool = False,
        mfa_secret: str | None = None,
        roles: list[str] | None = None,
        permissions: set[str] | None = None,
        last_login_at: datetime | None = None,
        last_login_ip: str | None = None,
        google_id: str | None = None,
        microsoft_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.avatar_url = avatar_url
        self.phone = phone
        self.is_active = is_active
        self.is_verified = is_verified
        self.mfa_enabled = mfa_enabled
        self.mfa_secret = mfa_secret
        self.roles = roles or []
        self.permissions = permissions or set()
        self.last_login_at = last_login_at
        self.last_login_ip = last_login_ip
        self.google_id = google_id
        self.microsoft_id = microsoft_id

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        email: Email,
        password_hash: HashedPassword,
        full_name: str,
    ) -> "User":
        """Factory method for creating a new user with registration event."""
        user = cls(
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
        )
        user.add_domain_event(
            UserRegistered(
                user_id=user.id,
                tenant_id=tenant_id,
                email=str(email),
            )
        )
        return user

    def record_login(self, ip_address: str | None = None) -> None:
        """Record a successful login attempt."""
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.add_domain_event(
            UserLoggedIn(user_id=self.id, ip_address=ip_address)
        )

    def change_password(self, new_password_hash: HashedPassword) -> None:
        """Change the user's password."""
        self.password_hash = new_password_hash
        self.updated_at = datetime.utcnow()
        self.add_domain_event(PasswordChanged(user_id=self.id))

    def enable_mfa(self, secret: str) -> None:
        """Enable MFA with the given TOTP secret."""
        self.mfa_enabled = True
        self.mfa_secret = secret
        self.updated_at = datetime.utcnow()
        self.add_domain_event(MFAEnabled(user_id=self.id))

    def disable_mfa(self) -> None:
        """Disable MFA."""
        self.mfa_enabled = False
        self.mfa_secret = None
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def verify_email(self) -> None:
        """Mark the user's email as verified."""
        self.is_verified = True
        self.updated_at = datetime.utcnow()

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if user has any of the given permissions."""
        return bool(self.permissions & set(permissions))

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
