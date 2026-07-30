"""Unit tests for auth domain value objects."""

import pytest

from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.password import HashedPassword, PlainPassword


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email(self):
        email = Email("User@Example.COM")
        assert email.value == "user@example.com"
        assert str(email) == "user@example.com"

    def test_email_domain(self):
        email = Email("john@company.io")
        assert email.domain == "company.io"

    def test_email_local_part(self):
        email = Email("john.doe@company.io")
        assert email.local_part == "john.doe"

    def test_empty_email_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Email("")

    def test_whitespace_email_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Email("   ")

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("not-an-email")

    def test_missing_at_sign_raises(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("userexample.com")

    def test_missing_domain_raises(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("user@")

    def test_email_normalization(self):
        email = Email("  John@Example.COM  ")
        assert email.value == "john@example.com"

    def test_email_equality(self):
        email1 = Email("user@example.com")
        email2 = Email("USER@EXAMPLE.COM")
        assert email1 == email2

    def test_email_with_plus(self):
        email = Email("user+tag@example.com")
        assert email.value == "user+tag@example.com"

    def test_email_max_length(self):
        long_local = "a" * 300
        with pytest.raises(ValueError, match="exceeds maximum length"):
            Email(f"{long_local}@example.com")


class TestPlainPassword:
    """Tests for PlainPassword value object."""

    def test_valid_password(self):
        pwd = PlainPassword("MyStr0ng!Pass")
        assert pwd.value == "MyStr0ng!Pass"

    def test_str_masks_value(self):
        pwd = PlainPassword("MyStr0ng!Pass")
        assert str(pwd) == "********"
        assert "MyStr0ng" not in repr(pwd)

    def test_empty_password_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            PlainPassword("")

    def test_short_password_raises(self):
        with pytest.raises(ValueError, match="at least 8 characters"):
            PlainPassword("Ab1!")

    def test_too_long_password_raises(self):
        long_pwd = "A" * 100 + "a1!" + "b" * 30
        with pytest.raises(ValueError, match="cannot exceed"):
            PlainPassword(long_pwd)

    def test_no_uppercase_raises(self):
        with pytest.raises(ValueError, match="uppercase"):
            PlainPassword("mystr0ng!pass")

    def test_no_lowercase_raises(self):
        with pytest.raises(ValueError, match="lowercase"):
            PlainPassword("MYSTR0NG!PASS")

    def test_no_digit_raises(self):
        with pytest.raises(ValueError, match="digit"):
            PlainPassword("MyStrong!Pass")

    def test_no_special_char_raises(self):
        with pytest.raises(ValueError, match="special character"):
            PlainPassword("MyStr0ngPass1")

    def test_minimum_valid_password(self):
        # Exactly 8 chars with all requirements
        pwd = PlainPassword("Ab1!cdef")
        assert pwd.value == "Ab1!cdef"


class TestHashedPassword:
    """Tests for HashedPassword value object."""

    def test_valid_bcrypt_hash(self):
        # bcrypt hash format
        hash_value = "$2b$12$LJ3m4lKx0z3q5v6w7x8y9OuRsT1u2V3w4X5y6Z7a8B9c0D1e2F3g"
        hp = HashedPassword(hash_value)
        assert hp.value == hash_value

    def test_empty_hash_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            HashedPassword("")

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid password hash"):
            HashedPassword("not-a-hash")

    def test_str_masks_value(self):
        hash_value = "$2b$12$LJ3m4lKx0z3q5v6w7x8y9OuRsT1u2V3w4X5y6Z7a8B9c0D1e2F3g"
        hp = HashedPassword(hash_value)
        assert "$2b$" not in str(hp)
        assert "***" in str(hp)
