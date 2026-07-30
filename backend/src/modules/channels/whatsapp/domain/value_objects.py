"""Value objects for the WhatsApp bounded context."""

from dataclasses import dataclass, field
from enum import Enum


class WhatsAppMessageType(str, Enum):
    """Types of WhatsApp messages."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    REACTION = "reaction"
    ORDER = "order"


class WhatsAppMessageStatus(str, Enum):
    """Delivery status from Meta webhooks."""

    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class InteractiveType(str, Enum):
    """Types of interactive messages."""

    BUTTON = "button"
    LIST = "list"
    PRODUCT = "product"
    PRODUCT_LIST = "product_list"
    FLOW = "flow"


class TemplateStatus(str, Enum):
    """WhatsApp template approval status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TemplateCategory(str, Enum):
    """Template categories as defined by Meta."""

    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"


@dataclass(frozen=True)
class WhatsAppMedia:
    """Media attachment in a WhatsApp message."""

    media_id: str | None = None  # Meta media ID
    url: str | None = None  # Download URL (temporary)
    mime_type: str = ""
    sha256: str | None = None
    file_size: int = 0
    filename: str | None = None  # For documents
    caption: str | None = None

    def to_dict(self) -> dict:
        return {
            k: v for k, v in {
                "id": self.media_id,
                "link": self.url,
                "mime_type": self.mime_type,
                "filename": self.filename,
                "caption": self.caption,
            }.items() if v is not None
        }


@dataclass(frozen=True)
class InteractiveButton:
    """A button in an interactive message."""

    id: str
    title: str  # Max 20 chars

    def to_dict(self) -> dict:
        return {"type": "reply", "reply": {"id": self.id, "title": self.title[:20]}}


@dataclass(frozen=True)
class ListSection:
    """A section in a list message."""

    title: str
    rows: list[dict] = field(default_factory=list)
    # rows: [{"id": "row_id", "title": "Row Title", "description": "optional"}]

    def to_dict(self) -> dict:
        return {"title": self.title, "rows": self.rows}


@dataclass(frozen=True)
class TemplateComponent:
    """A component in a template message (header, body, button)."""

    type: str  # "header", "body", "button"
    parameters: list[dict] = field(default_factory=list)
    # parameters: [{"type": "text", "text": "value"}]
    sub_type: str | None = None  # For buttons: "quick_reply", "url"
    index: int | None = None  # Button index

    def to_dict(self) -> dict:
        d: dict = {"type": self.type, "parameters": self.parameters}
        if self.sub_type:
            d["sub_type"] = self.sub_type
        if self.index is not None:
            d["index"] = str(self.index)
        return d
