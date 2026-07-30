"""Interfaces for the WhatsApp module."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.modules.channels.whatsapp.domain.entities import (
    WhatsAppConfig,
    WhatsAppTemplate,
)
from src.modules.channels.whatsapp.domain.value_objects import (
    InteractiveButton,
    ListSection,
    TemplateComponent,
    WhatsAppMedia,
    WhatsAppMessageType,
)


@dataclass
class OutboundMessage:
    """A message to be sent via WhatsApp."""

    to: str  # Recipient phone number (E.164)
    message_type: WhatsAppMessageType = WhatsAppMessageType.TEXT
    text: str | None = None
    media: WhatsAppMedia | None = None
    # Interactive
    interactive_type: str | None = None
    header: str | None = None
    body: str | None = None
    footer: str | None = None
    buttons: list[InteractiveButton] = field(default_factory=list)
    sections: list[ListSection] = field(default_factory=list)
    # Template
    template_name: str | None = None
    template_language: str = "es"
    template_components: list[TemplateComponent] = field(default_factory=list)


@dataclass
class InboundMessage:
    """A message received from WhatsApp webhook."""

    message_id: str  # WhatsApp message ID (wamid.xxx)
    from_number: str  # Sender phone (E.164)
    timestamp: str
    message_type: WhatsAppMessageType
    text: str | None = None
    media: WhatsAppMedia | None = None
    # Interactive reply
    button_reply_id: str | None = None
    button_reply_title: str | None = None
    list_reply_id: str | None = None
    list_reply_title: str | None = None
    # Context (reply-to)
    context_message_id: str | None = None
    # Sender profile
    profile_name: str | None = None


@dataclass
class SendResult:
    """Result of sending a WhatsApp message."""

    success: bool
    message_id: str | None = None  # wamid returned by Meta
    error_code: int | None = None
    error_message: str | None = None


class IWhatsAppClient(ABC):
    """Port for WhatsApp Cloud API operations."""

    @abstractmethod
    async def send_message(
        self, config: WhatsAppConfig, message: OutboundMessage
    ) -> SendResult:
        """Send a message via WhatsApp Cloud API."""
        ...

    @abstractmethod
    async def send_template(
        self, config: WhatsAppConfig, message: OutboundMessage
    ) -> SendResult:
        """Send a template message."""
        ...

    @abstractmethod
    async def mark_as_read(
        self, config: WhatsAppConfig, message_id: str
    ) -> bool:
        """Mark a message as read."""
        ...

    @abstractmethod
    async def download_media(
        self, config: WhatsAppConfig, media_id: str
    ) -> bytes | None:
        """Download media by its Meta media ID."""
        ...

    @abstractmethod
    async def upload_media(
        self, config: WhatsAppConfig, file_path: str, mime_type: str
    ) -> str | None:
        """Upload media and return the media ID."""
        ...


class IWhatsAppConfigRepository(ABC):
    """Port for WhatsApp config persistence."""

    @abstractmethod
    async def get_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> WhatsAppConfig | None: ...

    @abstractmethod
    async def get_by_phone_number_id(
        self, phone_number_id: str
    ) -> WhatsAppConfig | None: ...

    @abstractmethod
    async def create(self, config: WhatsAppConfig) -> WhatsAppConfig: ...

    @abstractmethod
    async def update(self, config: WhatsAppConfig) -> WhatsAppConfig: ...


class IWhatsAppTemplateRepository(ABC):
    """Port for template persistence."""

    @abstractmethod
    async def create(
        self, template: WhatsAppTemplate
    ) -> WhatsAppTemplate: ...

    @abstractmethod
    async def get_by_name(
        self, name: str, tenant_id: uuid.UUID
    ) -> WhatsAppTemplate | None: ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[WhatsAppTemplate]: ...

    @abstractmethod
    async def update(
        self, template: WhatsAppTemplate
    ) -> WhatsAppTemplate: ...

    @abstractmethod
    async def delete(
        self, template_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None: ...
