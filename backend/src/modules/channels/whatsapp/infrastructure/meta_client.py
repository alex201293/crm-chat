"""
Meta WhatsApp Cloud API client.
Implements IWhatsAppClient for sending messages, media, and templates
via the official Meta Graph API v18.0+.
"""

import hashlib
import hmac

import httpx
import structlog

from src.modules.channels.whatsapp.domain.entities import WhatsAppConfig
from src.modules.channels.whatsapp.domain.interfaces import (
    IWhatsAppClient,
    OutboundMessage,
    SendResult,
)
from src.modules.channels.whatsapp.domain.value_objects import (
    WhatsAppMessageType,
)

logger = structlog.get_logger()

META_API_BASE = "https://graph.facebook.com/v18.0"


class MetaWhatsAppClient(IWhatsAppClient):
    """
    WhatsApp Cloud API client using Meta's Graph API.
    Handles message construction, sending, media operations.
    """

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=30.0)

    async def send_message(
        self, config: WhatsAppConfig, message: OutboundMessage
    ) -> SendResult:
        """Send a message (text, media, or interactive)."""
        url = f"{META_API_BASE}/{config.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }

        payload = self._build_message_payload(message)

        try:
            response = await self._http.post(url, headers=headers, json=payload)
            data = response.json()

            if response.status_code == 200 and "messages" in data:
                msg_id = data["messages"][0]["id"]
                logger.info(
                    "WhatsApp message sent",
                    to=message.to,
                    message_id=msg_id,
                )
                return SendResult(success=True, message_id=msg_id)

            error = data.get("error", {})
            logger.error(
                "WhatsApp send failed",
                status=response.status_code,
                error=error,
            )
            return SendResult(
                success=False,
                error_code=error.get("code"),
                error_message=error.get("message", "Unknown error"),
            )

        except httpx.HTTPError as e:
            logger.error("WhatsApp HTTP error", error=str(e))
            return SendResult(
                success=False, error_message=str(e)
            )

    async def send_template(
        self, config: WhatsAppConfig, message: OutboundMessage
    ) -> SendResult:
        """Send a template message."""
        url = f"{META_API_BASE}/{config.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": message.to,
            "type": "template",
            "template": {
                "name": message.template_name,
                "language": {"code": message.template_language},
            },
        }

        # Add template components if provided
        if message.template_components:
            payload["template"]["components"] = [
                c.to_dict() for c in message.template_components
            ]

        try:
            response = await self._http.post(url, headers=headers, json=payload)
            data = response.json()

            if response.status_code == 200 and "messages" in data:
                return SendResult(
                    success=True, message_id=data["messages"][0]["id"]
                )

            error = data.get("error", {})
            return SendResult(
                success=False,
                error_code=error.get("code"),
                error_message=error.get("message"),
            )
        except httpx.HTTPError as e:
            return SendResult(success=False, error_message=str(e))

    async def mark_as_read(
        self, config: WhatsAppConfig, message_id: str
    ) -> bool:
        """Mark a received message as read (blue ticks)."""
        url = f"{META_API_BASE}/{config.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        try:
            response = await self._http.post(url, headers=headers, json=payload)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def download_media(
        self, config: WhatsAppConfig, media_id: str
    ) -> bytes | None:
        """Download media file by Meta media ID."""
        # Step 1: Get media URL
        url = f"{META_API_BASE}/{media_id}"
        headers = {"Authorization": f"Bearer {config.access_token}"}

        try:
            response = await self._http.get(url, headers=headers)
            if response.status_code != 200:
                return None

            media_url = response.json().get("url")
            if not media_url:
                return None

            # Step 2: Download the actual file
            file_response = await self._http.get(
                media_url, headers=headers
            )
            if file_response.status_code == 200:
                return file_response.content
            return None

        except httpx.HTTPError as e:
            logger.error("Media download failed", error=str(e))
            return None

    async def upload_media(
        self, config: WhatsAppConfig, file_path: str, mime_type: str
    ) -> str | None:
        """Upload a file and return its Meta media ID."""
        url = f"{META_API_BASE}/{config.phone_number_id}/media"
        headers = {"Authorization": f"Bearer {config.access_token}"}

        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (file_path.split("/")[-1], f, mime_type),
                }
                data = {
                    "messaging_product": "whatsapp",
                    "type": mime_type,
                }
                response = await self._http.post(
                    url, headers=headers, data=data, files=files
                )

            if response.status_code == 200:
                return response.json().get("id")
            return None

        except (httpx.HTTPError, OSError) as e:
            logger.error("Media upload failed", error=str(e))
            return None

    def _build_message_payload(self, message: OutboundMessage) -> dict:
        """Build the API payload based on message type."""
        payload: dict = {
            "messaging_product": "whatsapp",
            "to": message.to,
            "type": message.message_type.value,
        }

        if message.message_type == WhatsAppMessageType.TEXT:
            payload["text"] = {"body": message.text}

        elif message.message_type in (
            WhatsAppMessageType.IMAGE,
            WhatsAppMessageType.AUDIO,
            WhatsAppMessageType.VIDEO,
            WhatsAppMessageType.DOCUMENT,
        ):
            media_data = {}
            if message.media:
                if message.media.media_id:
                    media_data["id"] = message.media.media_id
                elif message.media.url:
                    media_data["link"] = message.media.url
                if message.media.caption:
                    media_data["caption"] = message.media.caption
                if message.media.filename:
                    media_data["filename"] = message.media.filename
            payload[message.message_type.value] = media_data

        elif message.message_type == WhatsAppMessageType.INTERACTIVE:
            interactive: dict = {"type": message.interactive_type or "button"}

            if message.header:
                interactive["header"] = {"type": "text", "text": message.header}
            if message.body:
                interactive["body"] = {"text": message.body}
            if message.footer:
                interactive["footer"] = {"text": message.footer}

            if message.interactive_type == "button" and message.buttons:
                interactive["action"] = {
                    "buttons": [b.to_dict() for b in message.buttons[:3]]
                }
            elif message.interactive_type == "list" and message.sections:
                interactive["action"] = {
                    "button": "Menu",
                    "sections": [s.to_dict() for s in message.sections],
                }

            payload["interactive"] = interactive

        elif message.message_type == WhatsAppMessageType.LOCATION:
            # Location handled via media metadata
            pass

        return payload


def verify_webhook_signature(
    payload: bytes, signature: str, app_secret: str
) -> bool:
    """
    Verify that a webhook payload was sent by Meta.
    Uses HMAC-SHA256 with the app secret.
    """
    expected = hmac.new(
        app_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
