"""
Use case: Refresh an access token using a valid refresh token.
Implements token rotation for security.
"""

from dataclasses import dataclass

from src.modules.auth.domain.interfaces.token_service import ITokenService, TokenPair
from src.modules.auth.domain.interfaces.user_repository import IUserRepository
from src.modules.auth.infrastructure.services.jwt_token_service import JWTTokenService
from src.shared.api.exceptions import AuthenticationError


@dataclass
class RefreshTokenCommand:
    """Input for token refresh."""

    refresh_token: str
    ip_address: str | None = None
    device_info: str | None = None


@dataclass
class RefreshTokenResult:
    """Output of successful token refresh."""

    tokens: TokenPair


class RefreshTokenHandler:
    """
    Orchestrates token refresh with rotation:
    1. Validate the refresh token
    2. Revoke the old refresh token
    3. Issue a new token pair
    4. Store the new refresh token
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        token_service: ITokenService,
    ) -> None:
        self._user_repo = user_repository
        self._token_service = token_service

    async def execute(self, command: RefreshTokenCommand) -> RefreshTokenResult:
        # Decode the refresh token to get user info
        # Refresh tokens are opaque, so we need to look up by hash
        token_hash = JWTTokenService.hash_token(command.refresh_token)

        # We need to find the user associated with this token
        # The validate method checks existence and expiration
        # First, let's try to find the token in the DB via the service
        # Since we can't directly query the user from the token service interface,
        # we need to find the user through the token validation

        # Attempt validation with a placeholder user_id — we'll look up properly
        # Actually, we store the token hash, so let's validate differently
        # We'll revoke the old one and issue new tokens

        # For this implementation, we need a way to find user by refresh token
        # Let's use the token service to validate and get the associated user
        from sqlalchemy import select

        from src.modules.auth.infrastructure.models import RefreshTokenModel

        # This is handled via the token service's internal session
        # We validate the token exists and is not revoked, then get user_id
        is_valid = False
        user_id = None

        # Access the underlying session through the token service
        # In production, we'd add a method to ITokenService for this
        if hasattr(self._token_service, "_session"):
            session = self._token_service._session  # type: ignore[attr-defined]
            from datetime import datetime

            stmt = select(RefreshTokenModel).where(
                RefreshTokenModel.token_hash == token_hash,
                RefreshTokenModel.is_revoked.is_(False),
                RefreshTokenModel.expires_at > datetime.utcnow(),
            )
            result = await session.execute(stmt)
            token_model = result.scalar_one_or_none()
            if token_model:
                is_valid = True
                user_id = token_model.user_id

        if not is_valid or not user_id:
            raise AuthenticationError("Invalid or expired refresh token")

        # Revoke old token
        await self._token_service.revoke_refresh_token(command.refresh_token)

        # Get user to build new token claims
        # We need to find the user without tenant_id scope
        from src.modules.auth.domain.value_objects.email import Email

        # Use a direct query since we have user_id
        if hasattr(self._user_repo, "_session"):
            from sqlalchemy.orm import selectinload

            from src.modules.auth.infrastructure.models import RoleModel, UserModel

            session = self._user_repo._session  # type: ignore[attr-defined]
            stmt = (
                select(UserModel)
                .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
                .where(UserModel.id == user_id, UserModel.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()

            if not user_model or not user_model.is_active:
                raise AuthenticationError("User account is not active")

            roles = [r.name for r in user_model.roles] if user_model.roles else []
            permissions: list[str] = []
            if user_model.roles:
                for role in user_model.roles:
                    if role.permissions:
                        permissions.extend(p.code for p in role.permissions)

            # Issue new tokens
            tokens = self._token_service.create_token_pair(
                user_id=user_model.id,
                tenant_id=user_model.tenant_id,
                email=user_model.email,
                roles=roles,
                permissions=list(set(permissions)),
            )

            # Store new refresh token
            await self._token_service.store_refresh_token(
                user_id=user_model.id,
                token_hash=JWTTokenService.hash_token(tokens.refresh_token),
                device_info=command.device_info,
                ip_address=command.ip_address,
                expires_at=tokens.refresh_token_expires_at,
            )

            return RefreshTokenResult(tokens=tokens)

        raise AuthenticationError("Unable to refresh token")
