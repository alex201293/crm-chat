"""Domain events for the Auth bounded context."""

import uuid

from src.shared.domain.base_entity import DomainEvent


class UserRegistered(DomainEvent):
    """Emitted when a new user registers."""

    def __init__(self, user_id: uuid.UUID, tenant_id: uuid.UUID, email: str) -> None:
        super().__init__()
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email


class UserLoggedIn(DomainEvent):
    """Emitted when a user logs in successfully."""

    def __init__(self, user_id: uuid.UUID, ip_address: str | None = None) -> None:
        super().__init__()
        self.user_id = user_id
        self.ip_address = ip_address


class PasswordChanged(DomainEvent):
    """Emitted when a user changes their password."""

    def __init__(self, user_id: uuid.UUID) -> None:
        super().__init__()
        self.user_id = user_id


class MFAEnabled(DomainEvent):
    """Emitted when a user enables MFA."""

    def __init__(self, user_id: uuid.UUID) -> None:
        super().__init__()
        self.user_id = user_id


class PasswordResetRequested(DomainEvent):
    """Emitted when a user requests a password reset."""

    def __init__(self, user_id: uuid.UUID, email: str) -> None:
        super().__init__()
        self.user_id = user_id
        self.email = email


class UserDeactivated(DomainEvent):
    """Emitted when a user account is deactivated."""

    def __init__(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        super().__init__()
        self.user_id = user_id
        self.tenant_id = tenant_id
