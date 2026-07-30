"""Password value objects for domain layer."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PlainPassword:
    """
    Plain text password value object.
    Validates password strength requirements.
    Never stored - only used during registration/change password flow.
    """

    value: str

    MIN_LENGTH = 8
    MAX_LENGTH = 128

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Password cannot be empty")

        if len(self.value) < self.MIN_LENGTH:
            raise ValueError(
                f"Password must be at least {self.MIN_LENGTH} characters"
            )

        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"Password cannot exceed {self.MAX_LENGTH} characters"
            )

        if not re.search(r"[A-Z]", self.value):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )

        if not re.search(r"[a-z]", self.value):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )

        if not re.search(r"\d", self.value):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", self.value):
            raise ValueError(
                "Password must contain at least one special character"
            )

    def __str__(self) -> str:
        return "********"  # Never expose the plain password

    def __repr__(self) -> str:
        return "PlainPassword(***)"


@dataclass(frozen=True)
class HashedPassword:
    """
    Hashed password value object.
    Wraps the bcrypt hash. Created by the security infrastructure.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Hashed password cannot be empty")

        # Basic check that it looks like a bcrypt hash
        if not self.value.startswith("$2"):
            raise ValueError("Invalid password hash format")

    def __str__(self) -> str:
        return "HashedPassword(***)"

    def __repr__(self) -> str:
        return "HashedPassword(***)"
