"""Value objects for the Chat bounded context."""

from dataclasses import dataclass, field
from enum import Enum


class Channel(str, Enum):
    """Communication channels supported by the platform."""

    WEB = "web"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    SMS = "sms"


class ConversationStatus(str, Enum):
    """Lifecycle states of a conversation."""

    ACTIVE = "active"
    PENDING = "pending"  # Waiting for agent assignment
    RESOLVED = "resolved"
    CLOSED = "closed"


class ConversationPriority(str, Enum):
    """Priority levels for conversations."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageSenderType(str, Enum):
    """Who sent the message."""

    USER = "user"  # End user / contact
    AGENT = "agent"  # Human agent
    AI = "ai"  # AI assistant
    SYSTEM = "system"  # System notifications


class MessageContentType(str, Enum):
    """Type of content in a message."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    TEMPLATE = "template"  # WhatsApp templates
    INTERACTIVE = "interactive"  # Buttons, lists


class MessageStatus(str, Enum):
    """Delivery status of outbound messages."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass(frozen=True)
class Attachment:
    """File attachment on a message."""

    url: str
    filename: str
    mime_type: str
    size_bytes: int

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size": self.size_bytes,
        }


@dataclass(frozen=True)
class EscalationReason:
    """Reason for escalating a conversation to a human agent."""

    reason_type: str  # "low_confidence", "user_request", "frustration", "complaint", "custom"
    description: str
    ai_confidence: float | None = None

    @classmethod
    def low_confidence(cls, confidence: float) -> "EscalationReason":
        return cls(
            reason_type="low_confidence",
            description=f"AI confidence below threshold: {confidence:.2f}",
            ai_confidence=confidence,
        )

    @classmethod
    def user_request(cls) -> "EscalationReason":
        return cls(
            reason_type="user_request",
            description="User explicitly requested a human agent",
        )

    @classmethod
    def frustration_detected(cls) -> "EscalationReason":
        return cls(
            reason_type="frustration",
            description="Frustration or complaint detected in user message",
        )
