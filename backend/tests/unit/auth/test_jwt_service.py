"""Unit tests for JWT token service (decode/encode only, no DB)."""

import os
import uuid
from unittest.mock import patch

import pytest

from src.modules.auth.infrastructure.services.jwt_token_service import JWTTokenService
from src.shared.api.exceptions import AuthenticationError


class TestJWTTokenServiceEncodeDecode:
    """Tests for JWT encode/decode (stateless operations, no DB session needed)."""

    def setup_method(self):
        """Set up environment and create a mock-session service."""
        # Patch settings to avoid needing .env file
        self._env_patcher = patch.dict(os.environ, {
            "APP_SECRET_KEY": "test-secret-key-at-least-32-characters-long",
            "JWT_SECRET_KEY": "test-jwt-secret-for-testing-only",
            "JWT_ALGORITHM": "HS256",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
        })
        self._env_patcher.start()

        # Clear settings cache so it picks up test env
        from src.config.settings import get_settings
        get_settings.cache_clear()

        # Create service with None session (only testing encode/decode)
        self.service = JWTTokenService(session=None)  # type: ignore

    def teardown_method(self):
        self._env_patcher.stop()
        from src.config.settings import get_settings
        get_settings.cache_clear()

    def test_create_token_pair(self):
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        pair = self.service.create_token_pair(
            user_id=user_id,
            tenant_id=tenant_id,
            email="user@example.com",
            roles=["admin"],
            permissions=["conversations:read"],
        )

        assert pair.access_token is not None
        assert pair.refresh_token is not None
        assert pair.refresh_token.startswith("rt_")
        assert pair.token_type == "Bearer"
        assert pair.access_token_expires_at is not None
        assert pair.refresh_token_expires_at is not None

    def test_decode_valid_token(self):
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        pair = self.service.create_token_pair(
            user_id=user_id,
            tenant_id=tenant_id,
            email="user@example.com",
            roles=["agent"],
            permissions=["conversations:read", "contacts:write"],
        )

        payload = self.service.decode_access_token(pair.access_token)

        assert payload.user_id == user_id
        assert payload.tenant_id == tenant_id
        assert payload.email == "user@example.com"
        assert "agent" in payload.roles
        assert "conversations:read" in payload.permissions
        assert payload.jti is not None

    def test_decode_expired_token_raises(self):
        from datetime import datetime, timedelta
        import jwt as pyjwt

        # Create an already-expired token
        payload = {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "email": "test@test.com",
            "roles": [],
            "permissions": [],
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
            "jti": str(uuid.uuid4()),
            "type": "access",
        }
        expired_token = pyjwt.encode(
            payload, "test-jwt-secret-for-testing-only", algorithm="HS256"
        )

        with pytest.raises(AuthenticationError, match="expired"):
            self.service.decode_access_token(expired_token)

    def test_decode_invalid_token_raises(self):
        with pytest.raises(AuthenticationError, match="Invalid"):
            self.service.decode_access_token("not.a.valid.token")

    def test_decode_wrong_secret_raises(self):
        import jwt as pyjwt

        payload = {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "email": "test@test.com",
            "roles": [],
            "permissions": [],
            "exp": 9999999999,
            "iat": 1000000000,
            "jti": str(uuid.uuid4()),
            "type": "access",
        }
        token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(AuthenticationError):
            self.service.decode_access_token(token)

    def test_decode_wrong_token_type_raises(self):
        import jwt as pyjwt
        from datetime import datetime, timedelta

        payload = {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "email": "test@test.com",
            "roles": [],
            "permissions": [],
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),
            "type": "refresh",  # Wrong type
        }
        token = pyjwt.encode(
            payload, "test-jwt-secret-for-testing-only", algorithm="HS256"
        )

        with pytest.raises(AuthenticationError, match="Invalid token type"):
            self.service.decode_access_token(token)

    def test_token_hash_is_deterministic(self):
        token = "rt_abc123def456"
        hash1 = JWTTokenService.hash_token(token)
        hash2 = JWTTokenService.hash_token(token)
        assert hash1 == hash2

    def test_different_tokens_different_hashes(self):
        hash1 = JWTTokenService.hash_token("rt_token1")
        hash2 = JWTTokenService.hash_token("rt_token2")
        assert hash1 != hash2

    def test_refresh_tokens_are_unique(self):
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        pair1 = self.service.create_token_pair(
            user_id=user_id, tenant_id=tenant_id,
            email="u@e.com", roles=[], permissions=[],
        )
        pair2 = self.service.create_token_pair(
            user_id=user_id, tenant_id=tenant_id,
            email="u@e.com", roles=[], permissions=[],
        )

        assert pair1.refresh_token != pair2.refresh_token
        assert pair1.access_token != pair2.access_token
