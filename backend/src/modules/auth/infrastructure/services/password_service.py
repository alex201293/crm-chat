"""Password hashing service using bcrypt."""

from src.modules.auth.domain.value_objects.password import HashedPassword, PlainPassword
from src.shared.infrastructure.security import hash_password, verify_password


class PasswordService:
    """
    Service for hashing and verifying passwords.
    Wraps the shared security infrastructure.
    """

    def hash(self, plain_password: PlainPassword) -> HashedPassword:
        """Hash a plain password and return a HashedPassword value object."""
        hashed = hash_password(plain_password.value)
        return HashedPassword(hashed)

    def verify(self, plain_password: str, hashed_password: HashedPassword) -> bool:
        """Verify a plain password against a stored hash."""
        return verify_password(plain_password, hashed_password.value)
