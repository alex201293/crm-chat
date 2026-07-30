"""Value objects for the CRM bounded context."""

from dataclasses import dataclass
from enum import Enum


class LifecycleStage(str, Enum):
    """Contact lifecycle stage in the marketing/sales funnel."""

    SUBSCRIBER = "subscriber"
    LEAD = "lead"
    MQL = "mql"  # Marketing Qualified Lead
    SQL = "sql"  # Sales Qualified Lead
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    EVANGELIST = "evangelist"


class DealStatus(str, Enum):
    """High-level deal status."""

    OPEN = "open"
    WON = "won"
    LOST = "lost"


class TaskStatus(str, Enum):
    """Task completion status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ActivityType(str, Enum):
    """Types of CRM activities."""

    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    MESSAGE = "message"
    TASK_COMPLETED = "task_completed"
    CONTACT_CREATED = "contact_created"


@dataclass(frozen=True)
class Money:
    """Monetary value with currency."""

    amount: int  # Stored in cents
    currency: str = "USD"

    @property
    def display(self) -> float:
        return self.amount / 100

    def __str__(self) -> str:
        return f"{self.display:.2f} {self.currency}"


@dataclass(frozen=True)
class Address:
    """Physical address value object."""

    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""

    def to_dict(self) -> dict:
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
        }
