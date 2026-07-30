"""Email value object with strict validation."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """
    Immutable email value object.
    Validates format and normalizes to lowercase.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Email cannot be empty")

        normalized = self.value.lower().strip()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, normalized):
            raise ValueError(f"Invalid email format: {self.value}")

        if len(normalized) > 320:
            raise ValueError("Email exceeds maximum length of 320 characters")

        # Frozen dataclass workaround for normalization
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    @property
    def domain(self) -> str:
        """Extract domain from email."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part from email."""
        return self.value.split("@")[0]
