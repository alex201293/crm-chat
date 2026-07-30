"""Unit tests for auth infrastructure services (no DB required)."""

import pytest

from src.modules.auth.domain.value_objects.password import HashedPassword, PlainPassword
from src.modules.auth.infrastructure.services.mfa_service import MFAService
from src.modules.auth.infrastructure.services.password_service import PasswordService


class TestPasswordService:
    """Tests for password hashing and verification."""

    def setup_method(self):
        self.service = PasswordService()

    def test_hash_returns_hashed_password(self):
        plain = PlainPassword("MyStr0ng!Pass")
        hashed = self.service.hash(plain)

        assert isinstance(hashed, HashedPassword)
        assert hashed.value.startswith("$2")
        assert hashed.value != plain.value

    def test_verify_correct_password(self):
        plain = PlainPassword("MyStr0ng!Pass")
        hashed = self.service.hash(plain)

        assert self.service.verify("MyStr0ng!Pass", hashed) is True

    def test_verify_incorrect_password(self):
        plain = PlainPassword("MyStr0ng!Pass")
        hashed = self.service.hash(plain)

        assert self.service.verify("WrongPass1!", hashed) is False

    def test_same_password_different_hashes(self):
        plain = PlainPassword("MyStr0ng!Pass")
        hash1 = self.service.hash(plain)
        hash2 = self.service.hash(plain)

        # bcrypt generates unique salt each time
        assert hash1.value != hash2.value

        # Both should verify correctly
        assert self.service.verify("MyStr0ng!Pass", hash1) is True
        assert self.service.verify("MyStr0ng!Pass", hash2) is True


class TestMFAService:
    """Tests for TOTP MFA service."""

    def setup_method(self):
        self.service = MFAService()

    def test_generate_secret(self):
        secret = self.service.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) == 32  # base32 encoded, 32 chars

    def test_generate_unique_secrets(self):
        secret1 = self.service.generate_secret()
        secret2 = self.service.generate_secret()
        assert secret1 != secret2

    def test_provisioning_uri(self):
        secret = self.service.generate_secret()
        uri = self.service.get_provisioning_uri(
            secret=secret, email="user@example.com"
        )

        assert uri.startswith("otpauth://totp/")
        assert "user%40example.com" in uri or "user@example.com" in uri
        assert "CRM+Chat" in uri or "CRM%20Chat" in uri
        assert f"secret={secret}" in uri

    def test_verify_current_code(self):
        secret = self.service.generate_secret()
        current_code = self.service.get_current_code(secret)

        assert self.service.verify_code(secret, current_code) is True

    def test_verify_invalid_code(self):
        secret = self.service.generate_secret()
        assert self.service.verify_code(secret, "000000") is False

    def test_verify_wrong_secret(self):
        secret1 = self.service.generate_secret()
        secret2 = self.service.generate_secret()
        code = self.service.get_current_code(secret1)

        assert self.service.verify_code(secret2, code) is False
