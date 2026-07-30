"""
Shared value objects used across multiple bounded contexts.
Value objects are immutable and compared by value, not identity.
"""

import re
from dataclasses import dataclass

import phonenumbers


@dataclass(frozen=True)
class Email:
    """Email value object with validation."""

    value: str

    def __post_init__(self) -> None:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid email format: {self.value}")
        # Normalize to lowercase
        object.__setattr__(self, "value", self.value.lower().strip())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PhoneNumber:
    """Phone number value object with international format validation."""

    value: str
    country_code: str = "US"

    def __post_init__(self) -> None:
        try:
            parsed = phonenumbers.parse(self.value, self.country_code)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError(f"Invalid phone number: {self.value}")
            # Store in E.164 format
            formatted = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
            object.__setattr__(self, "value", formatted)
        except phonenumbers.NumberParseException as e:
            raise ValueError(f"Cannot parse phone number: {self.value}") from e

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Slug:
    """URL-safe slug value object."""

    value: str

    def __post_init__(self) -> None:
        pattern = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid slug format: {self.value}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Money:
    """Monetary value object with currency."""

    amount: int  # Store in smallest unit (cents)
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")
        object.__setattr__(self, "currency", self.currency.upper())

    @property
    def display_amount(self) -> float:
        return self.amount / 100

    def __str__(self) -> str:
        return f"{self.display_amount:.2f} {self.currency}"


@dataclass(frozen=True)
class Pagination:
    """Pagination value object for queries."""

    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
