"""JWT token service implementation."""

import hashlib
import uuid
from datetime import datetime, timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.modules.auth.domain.interfaces.token_service import (
    ITokenService,
    TokenPair,
    TokenPayload,
)
from src.modules.auth.infrastructure.models import RefreshTokenModel
from src.shared.api.exceptions import AuthenticationError


class JWTTokenService(ITokenService):
    """
    JWT-based token service.
    Access tokens are short-lived JWTs.
    Refresh tokens are opaque strings stored hashed in DB for rotation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        settings = get_settings()
        self._secret_key = settings.jwt.JWT_SECRET_KEY
        self._algorithm = settings.jwt.JWT_ALGORITHM
        self._access_expire_minutes = settings.jwt.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_expire_days = settings.jwt.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def create_token_pair(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        email: str,
        roles: list[str],
        permissions: list[str],
    ) -> TokenPair:
        now = datetime.utcnow()
        access_expires = now + timedelta(minutes=self._access_expire_minutes)
        refresh_expires = now + timedelta(days=self._refresh_expire_days)
        jti = str(uuid.uuid4())

        # Access token (JWT)
        access_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "email": email,
            "roles": roles,
            "permissions": permissions,
            "exp": access_expires,
            "iat": now,
            "jti": jti,
            "type": "access",
        }
        access_token = jwt.encode(access_payload, self._secret_key, algorithm=self._algorithm)

        # Refresh token (opaque UUID-based token)
        refresh_token = f"rt_{uuid.uuid4().hex}{uuid.uuid4().hex}"

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_expires,
            refresh_token_expires_at=refresh_expires,
        )

    def decode_access_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Access token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid access token")

        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")

        return TokenPayload(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            email=payload["email"],
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            exp=datetime.utcfromtimestamp(payload["exp"]),
            iat=datetime.utcfromtimestamp(payload["iat"]),
            jti=payload["jti"],
        )

    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        device_info: str | None,
        ip_address: str | None,
        expires_at: datetime,
    ) -> None:
        model = RefreshTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def validate_refresh_token(self, token: str, user_id: uuid.UUID) -> bool:
        token_hash = self._hash_token(token)
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash,
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.is_revoked.is_(False),
            RefreshTokenModel.expires_at > datetime.utcnow(),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def revoke_refresh_token(self, token: str) -> None:
        token_hash = self._hash_token(token)
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self._session.execute(stmt)

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self._session.execute(stmt)

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a refresh token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def hash_token(token: str) -> str:
        """Public static method for hashing tokens (used by use cases)."""
        return hashlib.sha256(token.encode()).hexdigest()
