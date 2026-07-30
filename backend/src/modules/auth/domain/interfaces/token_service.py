"""Token service interface for JWT and refresh token management."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TokenPair:
    """Access + Refresh token pair."""

    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    token_type: str = "Bearer"


@dataclass
class TokenPayload:
    """Decoded JWT payload."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    roles: list[str]
    permissions: list[str]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for revocation


class ITokenService(ABC):
    """Port for token generation and validation."""

    @abstractmethod
    def create_token_pair(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        email: str,
        roles: list[str],
        permissions: list[str],
    ) -> TokenPair:
        """Generate a new access + refresh token pair."""
        ...

    @abstractmethod
    def decode_access_token(self, token: str) -> TokenPayload:
        """
        Decode and validate an access token.
        Raises AuthenticationError if invalid or expired.
        """
        ...

    @abstractmethod
    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        device_info: str | None,
        ip_address: str | None,
        expires_at: datetime,
    ) -> None:
        """Persist a refresh token hash for rotation tracking."""
        ...

    @abstractmethod
    async def validate_refresh_token(self, token: str, user_id: uuid.UUID) -> bool:
        """Validate a refresh token exists and is not revoked."""
        ...

    @abstractmethod
    async def revoke_refresh_token(self, token: str) -> None:
        """Revoke a specific refresh token."""
        ...

    @abstractmethod
    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user (forced logout)."""
        ...
