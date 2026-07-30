"""
Use cases: Enable MFA, Verify MFA setup, Disable MFA.
"""

import uuid
from dataclasses import dataclass

from src.modules.auth.domain.interfaces.user_repository import IUserRepository
from src.modules.auth.infrastructure.services.mfa_service import MFAService
from src.shared.api.exceptions import AuthenticationError, EntityNotFoundError
from src.shared.domain.events import event_bus


@dataclass
class EnableMFACommand:
    """Input for enabling MFA (step 1: generate secret)."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass
class EnableMFAResult:
    """Output with provisioning data for QR code."""

    secret: str
    provisioning_uri: str


@dataclass
class VerifyMFASetupCommand:
    """Input for verifying MFA setup (step 2: confirm code works)."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    code: str


@dataclass
class DisableMFACommand:
    """Input for disabling MFA."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    password: str


class EnableMFAHandler:
    """
    Step 1 of MFA setup: generates a TOTP secret and provisioning URI.
    Does NOT enable MFA yet - user must verify with a code first.
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        mfa_service: MFAService,
    ) -> None:
        self._user_repo = user_repository
        self._mfa_service = mfa_service

    async def execute(self, command: EnableMFACommand) -> EnableMFAResult:
        user = await self._user_repo.get_by_id(command.user_id, command.tenant_id)
        if not user:
            raise EntityNotFoundError("User", str(command.user_id))

        if user.mfa_enabled:
            raise AuthenticationError("MFA is already enabled")

        # Generate secret
        secret = self._mfa_service.generate_secret()
        provisioning_uri = self._mfa_service.get_provisioning_uri(
            secret=secret,
            email=str(user.email),
        )

        # Store secret temporarily (not enabled until verified)
        user.mfa_secret = secret
        await self._user_repo.update(user)

        return EnableMFAResult(
            secret=secret,
            provisioning_uri=provisioning_uri,
        )


class VerifyMFASetupHandler:
    """
    Step 2 of MFA setup: verifies the TOTP code and enables MFA.
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        mfa_service: MFAService,
    ) -> None:
        self._user_repo = user_repository
        self._mfa_service = mfa_service

    async def execute(self, command: VerifyMFASetupCommand) -> None:
        user = await self._user_repo.get_by_id(command.user_id, command.tenant_id)
        if not user:
            raise EntityNotFoundError("User", str(command.user_id))

        if not user.mfa_secret:
            raise AuthenticationError("MFA setup not initiated. Call enable first.")

        if user.mfa_enabled:
            raise AuthenticationError("MFA is already enabled")

        # Verify code
        if not self._mfa_service.verify_code(user.mfa_secret, command.code):
            raise AuthenticationError("Invalid MFA code. Please try again.")

        # Enable MFA
        user.enable_mfa(user.mfa_secret)
        await self._user_repo.update(user)

        # Publish events
        await event_bus.publish_all(user.clear_domain_events())


class DisableMFAHandler:
    """Disable MFA after verifying the user's password."""

    def __init__(
        self,
        user_repository: IUserRepository,
        password_service: "PasswordService",
    ) -> None:
        self._user_repo = user_repository
        self._password_service = password_service

    async def execute(self, command: DisableMFACommand) -> None:
        from src.modules.auth.infrastructure.services.password_service import PasswordService

        user = await self._user_repo.get_by_id(command.user_id, command.tenant_id)
        if not user:
            raise EntityNotFoundError("User", str(command.user_id))

        if not user.mfa_enabled:
            return  # Already disabled

        # Verify password for security
        if not user.password_hash:
            raise AuthenticationError("Cannot disable MFA without password")

        if not self._password_service.verify(command.password, user.password_hash):
            raise AuthenticationError("Invalid password")

        user.disable_mfa()
        await self._user_repo.update(user)
