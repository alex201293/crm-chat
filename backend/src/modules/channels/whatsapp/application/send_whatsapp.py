"""
Use case: Send a message to a contact via WhatsApp.
Used by agents, campaigns, and automated flows.
"""

import uuid
from dataclasses import dataclass, field

import structlog

from src.modules.channels.whatsapp.domain.interfaces import (
    IWhatsAppClient,
    IWhatsAppConfigRepository,
    OutboundMessage,
    SendResult,
)
from src.modules.channels.whatsapp.domain.value_objects import (
    InteractiveButton,
    ListSection,
    TemplateComponent,
    WhatsAppMedia,
    WhatsAppMessageType,
)
from src.shared.api.exceptions import EntityNotFoundError, ValidationError_

logger = structlog.get_logger()


@dataclass
class SendWhatsAppMessageCommand:
    """Command to send a WhatsApp message."""

    tenant_id: uuid.UUID
    to: str  # E.164 phone number
    # Text
    text: str | None = None
    # Media
    media_url: str | None = None
    media_type: str | None = None  # image, audio, video, document
    media_caption: str | None = None
    media_filename: str | None = None
    # Interactive buttons
    buttons: list[dict] | None = None  # [{"id": "x", "title": "Y"}]
    button_body: str | None = None
    button_header: str | None = None
    button_footer: str | None = None
    # Interactive list
    list_body: str | None = None
    list_sections: list[dict] | None = None
    # Template
    template_name: str | None = None
    template_language: str = "es"
    template_components: list[dict] | None = None


class SendWhatsAppMessageHandler:
    """
    Orchestrates sending a WhatsApp message:
    1. Load tenant's WhatsApp config
    2. Build the outbound message
    3. Send via Meta API
    4. Return result
    """

    def __init__(
        self,
        wa_client: IWhatsAppClient,
        config_repo: IWhatsAppConfigRepository,
    ) -> None:
        self._wa_client = wa_client
        self._config_repo = config_repo

    async def execute(self, cmd: SendWhatsAppMessageCommand) -> SendResult:
        # 1. Load config
        config = await self._config_repo.get_by_tenant(cmd.tenant_id)
        if not config:
            raise EntityNotFoundError("WhatsAppConfig", str(cmd.tenant_id))

        if not config.is_active:
            raise ValidationError_("WhatsApp is not active for this tenant")

        # 2. Build outbound message
        message = self._build_outbound(cmd)

        # 3. Send
        if cmd.template_name:
            result = await self._wa_client.send_template(config, message)
        else:
            result = await self._wa_client.send_message(config, message)

        if result.success:
            logger.info(
                "WhatsApp message sent",
                tenant_id=str(cmd.tenant_id),
                to=cmd.to,
                type=message.message_type.value,
                msg_id=result.message_id,
            )
        else:
            logger.error(
                "WhatsApp send failed",
                tenant_id=str(cmd.tenant_id),
                to=cmd.to,
                error=result.error_message,
            )

        return result

    def _build_outbound(self, cmd: SendWhatsAppMessageCommand) -> OutboundMessage:
        """Build OutboundMessage from command data."""

        # Template message
        if cmd.template_name:
            components = []
            if cmd.template_components:
                components = [
                    TemplateComponent(
                        type=c.get("type", "body"),
                        parameters=c.get("parameters", []),
                        sub_type=c.get("sub_type"),
                        index=c.get("index"),
                    )
                    for c in cmd.template_components
                ]
            return OutboundMessage(
                to=cmd.to,
                message_type=WhatsAppMessageType.TEMPLATE,
                template_name=cmd.template_name,
                template_language=cmd.template_language,
                template_components=components,
            )

        # Interactive buttons
        if cmd.buttons:
            buttons = [
                InteractiveButton(id=b["id"], title=b["title"])
                for b in cmd.buttons[:3]
            ]
            return OutboundMessage(
                to=cmd.to,
                message_type=WhatsAppMessageType.INTERACTIVE,
                interactive_type="button",
                header=cmd.button_header,
                body=cmd.button_body or cmd.text or "",
                footer=cmd.button_footer,
                buttons=buttons,
            )

        # Interactive list
        if cmd.list_sections:
            sections = [
                ListSection(
                    title=s.get("title", ""),
                    rows=s.get("rows", []),
                )
                for s in cmd.list_sections
            ]
            return OutboundMessage(
                to=cmd.to,
                message_type=WhatsAppMessageType.INTERACTIVE,
                interactive_type="list",
                body=cmd.list_body or cmd.text or "",
                sections=sections,
            )

        # Media message
        if cmd.media_url and cmd.media_type:
            media_type_map = {
                "image": WhatsAppMessageType.IMAGE,
                "audio": WhatsAppMessageType.AUDIO,
                "video": WhatsAppMessageType.VIDEO,
                "document": WhatsAppMessageType.DOCUMENT,
            }
            wa_type = media_type_map.get(
                cmd.media_type, WhatsAppMessageType.DOCUMENT
            )
            return OutboundMessage(
                to=cmd.to,
                message_type=wa_type,
                media=WhatsAppMedia(
                    url=cmd.media_url,
                    caption=cmd.media_caption,
                    filename=cmd.media_filename,
                ),
            )

        # Plain text
        return OutboundMessage(
            to=cmd.to,
            message_type=WhatsAppMessageType.TEXT,
            text=cmd.text or "",
        )
