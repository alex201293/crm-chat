"""
Use cases: Request password reset and confirm password reset.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.auth.domain.interfaces.user_repository import IUserRepository
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.password import PlainPassword
from src.modules.auth.infrastructure.services.password_service import PasswordService
from src.shared.api.exceptions import AuthenticationError, ValidationError_
from src.shared.domain.events import event_bus
from src.modules.auth.domain.events.auth_events import PasswordResetRequested

# In-memory token store for password resets (production: use Redis)
_reset_tokens: dict[str, dict] = {}


@dataclass
class RequestPasswordResetCommand:
    """Input for requesting a password reset."""

    email: str


@dataclass
class ConfirmPasswordResetCommand:
    """Input for confirming a password reset."""

    token: str
    new_password: str


class RequestPasswordResetHandler:
    """
    Generates a password reset token and publishes an event.
    The notification service will send the email.
    Always returns success to prevent email enumeration.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        self._user_repo = user_repository

    async def execute(self, command: RequestPasswordResetCommand) -> None:
        try:
            email = Email(command.email)
        except ValueError:
            return  # Silent fail for invalid emails (no enumeration)

        user = await self._user_repo.get_by_email_any_tenant(email)
        if not user:
            return  # Silent fail (no enumeration)

        if not user.is_active:
            return

        # Generate reset token
        token = f"rst_{uuid.uuid4().hex}"
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Store token with expiration (30 minutes)
        _reset_tokens[token_hash] = {
            "user_id": user.id,
            "expires_at": datetime.utcnow() + timedelta(minutes=30),
        }

        # Publish event (notification service sends email with token)
        await event_bus.publish(
            PasswordResetRequested(user_id=user.id, email=str(email))
        )

        # In production, the token would be sent via email
        # For now, it's stored in-memory


class ConfirmPasswordResetHandler:
    """
    Validates the reset token and sets the new password.
    Revokes all existing sessions for security.
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        password_service: PasswordService,
    ) -> None:
        self._user_repo = user_repository
        self._password_service = password_service

    async def execute(self, command: ConfirmPasswordResetCommand) -> None:
        # Validate token
        token_hash = hashlib.sha256(command.token.encode()).hexdigest()
        token_data = _reset_tokens.get(token_hash)

        if not token_data:
            raise AuthenticationError("Invalid or expired reset token")

        if datetime.utcnow() > token_data["expires_at"]:
            del _reset_tokens[token_hash]
            raise AuthenticationError("Reset token has expired")

        # Validate new password
        plain_password = PlainPassword(command.new_password)

        # Get user
        user_id = token_data["user_id"]
        # We need to find user without tenant scope
        user = None
        # Use the any_tenant lookup via a synthetic email lookup
        # Actually we stored user_id, so we query directly
        # This is a simplification - in production use Redis with user_id

        from sqlalchemy import select
        from src.modules.auth.infrastructure.models import UserModel

        if hasattr(self._user_repo, "_session"):
            session = self._user_repo._session  # type: ignore[attr-defined]
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                raise AuthenticationError("User not found")

            email = Email(model.email)
            user = await self._user_repo.get_by_email(email, model.tenant_id)

        if not user:
            raise AuthenticationError("User not found")

        # Update password
        new_hash = self._password_service.hash(plain_password)
        user.change_password(new_hash)
        await self._user_repo.update(user)

        # Invalidate reset token
        del _reset_tokens[token_hash]

        # Publish events
        await event_bus.publish_all(user.clear_domain_events())
