"""
Use case: Authenticate a user with email and password.
Handles MFA verification when enabled.
"""

from dataclasses import dataclass

from src.modules.auth.domain.interfaces.token_service import ITokenService, TokenPair
from src.modules.auth.domain.interfaces.user_repository import IUserRepository
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.infrastructure.services.jwt_token_service import JWTTokenService
from src.modules.auth.infrastructure.services.mfa_service import MFAService
from src.modules.auth.infrastructure.services.password_service import PasswordService
from src.shared.api.exceptions import AuthenticationError
from src.shared.domain.events import event_bus


@dataclass
class LoginUserCommand:
    """Input data for login."""

    email: str
    password: str
    mfa_code: str | None = None
    ip_address: str | None = None
    device_info: str | None = None


@dataclass
class LoginUserResult:
    """Output of successful login."""

    user_id: str
    tenant_id: str
    email: str
    full_name: str
    roles: list[str]
    mfa_required: bool
    tokens: TokenPair | None  # None if MFA is pending


class LoginUserHandler:
    """
    Orchestrates the login flow:
    1. Find user by email
    2. Verify password
    3. Check MFA if enabled
    4. Generate tokens
    5. Record login and publish events
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        token_service: ITokenService,
        password_service: PasswordService,
        mfa_service: MFAService,
    ) -> None:
        self._user_repo = user_repository
        self._token_service = token_service
        self._password_service = password_service
        self._mfa_service = mfa_service

    async def execute(self, command: LoginUserCommand) -> LoginUserResult:
        # 1. Find user
        email = Email(command.email)
        user = await self._user_repo.get_by_email_any_tenant(email)

        if not user:
            # Use constant-time response to prevent email enumeration
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        # 2. Verify password
        if not user.password_hash:
            raise AuthenticationError("Invalid email or password")

        if not self._password_service.verify(command.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        # 3. Check MFA
        if user.mfa_enabled:
            if not command.mfa_code:
                # MFA required but not provided - return partial result
                return LoginUserResult(
                    user_id=str(user.id),
                    tenant_id=str(user.tenant_id),
                    email=str(user.email),
                    full_name=user.full_name,
                    roles=user.roles,
                    mfa_required=True,
                    tokens=None,
                )

            # Verify MFA code
            if not user.mfa_secret:
                raise AuthenticationError("MFA configuration error")

            if not self._mfa_service.verify_code(user.mfa_secret, command.mfa_code):
                raise AuthenticationError("Invalid MFA code")

        # 4. Generate tokens
        tokens = self._token_service.create_token_pair(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=str(user.email),
            roles=user.roles,
            permissions=list(user.permissions),
        )

        # Store refresh token
        await self._token_service.store_refresh_token(
            user_id=user.id,
            token_hash=JWTTokenService.hash_token(tokens.refresh_token),
            device_info=command.device_info,
            ip_address=command.ip_address,
            expires_at=tokens.refresh_token_expires_at,
        )

        # 5. Record login
        user.record_login(ip_address=command.ip_address)
        await self._user_repo.update(user)

        # 6. Publish events
        await event_bus.publish_all(user.clear_domain_events())

        return LoginUserResult(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=str(user.email),
            full_name=user.full_name,
            roles=user.roles,
            mfa_required=False,
            tokens=tokens,
        )
