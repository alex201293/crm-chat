"""
WhatsApp webhook payload parser.
Transforms Meta's webhook JSON into domain InboundMessage objects.
Handles message types, statuses, and verification challenges.
"""

import structlog

from src.modules.channels.whatsapp.domain.interfaces import InboundMessage
from src.modules.channels.whatsapp.domain.value_objects import (
    WhatsAppMedia,
    WhatsAppMessageStatus,
    WhatsAppMessageType,
)

logger = structlog.get_logger()


def parse_webhook_payload(payload: dict) -> tuple[list[InboundMessage], list[dict]]:
    """
    Parse a Meta webhook payload into messages and status updates.

    Returns:
        tuple: (list of InboundMessages, list of status dicts)
    """
    messages: list[InboundMessage] = []
    statuses: list[dict] = []

    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # Parse incoming messages
            for msg_data in value.get("messages", []):
                parsed = _parse_message(msg_data, value)
                if parsed:
                    messages.append(parsed)

            # Parse status updates
            for status_data in value.get("statuses", []):
                statuses.append({
                    "message_id": status_data.get("id"),
                    "status": status_data.get("status"),
                    "timestamp": status_data.get("timestamp"),
                    "recipient_id": status_data.get("recipient_id"),
                    "errors": status_data.get("errors", []),
                })

    return messages, statuses


def _parse_message(msg_data: dict, value: dict) -> InboundMessage | None:
    """Parse a single message from webhook data."""
    try:
        msg_type_str = msg_data.get("type", "text")
        try:
            msg_type = WhatsAppMessageType(msg_type_str)
        except ValueError:
            msg_type = WhatsAppMessageType.TEXT

        from_number = msg_data.get("from", "")
        message_id = msg_data.get("id", "")
        timestamp = msg_data.get("timestamp", "")

        # Extract profile name from contacts
        profile_name = None
        contacts = value.get("contacts", [])
        if contacts:
            profile = contacts[0].get("profile", {})
            profile_name = profile.get("name")

        # Parse text
        text = None
        if msg_type == WhatsAppMessageType.TEXT:
            text = msg_data.get("text", {}).get("body")

        # Parse media
        media = None
        if msg_type in (
            WhatsAppMessageType.IMAGE,
            WhatsAppMessageType.AUDIO,
            WhatsAppMessageType.VIDEO,
            WhatsAppMessageType.DOCUMENT,
            WhatsAppMessageType.STICKER,
        ):
            media_data = msg_data.get(msg_type.value, {})
            media = WhatsAppMedia(
                media_id=media_data.get("id"),
                mime_type=media_data.get("mime_type", ""),
                sha256=media_data.get("sha256"),
                file_size=media_data.get("file_size", 0),
                filename=media_data.get("filename"),
                caption=media_data.get("caption"),
            )
            # Use caption as text content for display
            if media.caption:
                text = media.caption

        # Parse interactive replies
        button_reply_id = None
        button_reply_title = None
        list_reply_id = None
        list_reply_title = None

        if msg_type == WhatsAppMessageType.INTERACTIVE:
            interactive = msg_data.get("interactive", {})
            int_type = interactive.get("type")
            if int_type == "button_reply":
                reply = interactive.get("button_reply", {})
                button_reply_id = reply.get("id")
                button_reply_title = reply.get("title")
                text = button_reply_title
            elif int_type == "list_reply":
                reply = interactive.get("list_reply", {})
                list_reply_id = reply.get("id")
                list_reply_title = reply.get("title")
                text = list_reply_title

        # Context (reply-to)
        context_message_id = None
        context = msg_data.get("context")
        if context:
            context_message_id = context.get("id")

        return InboundMessage(
            message_id=message_id,
            from_number=from_number,
            timestamp=timestamp,
            message_type=msg_type,
            text=text,
            media=media,
            button_reply_id=button_reply_id,
            button_reply_title=button_reply_title,
            list_reply_id=list_reply_id,
            list_reply_title=list_reply_title,
            context_message_id=context_message_id,
            profile_name=profile_name,
        )

    except Exception as e:
        logger.error("Failed to parse WhatsApp message", error=str(e))
        return None


def get_phone_number_id_from_payload(payload: dict) -> str | None:
    """Extract the phone_number_id from a webhook payload."""
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")
            if phone_number_id:
                return phone_number_id
    return None
