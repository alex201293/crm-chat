"""
Security utilities: password hashing, JWT management, encryption.
Uses bcrypt directly (passlib has compatibility issues with Python 3.14+).
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
