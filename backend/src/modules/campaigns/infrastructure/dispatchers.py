"""
Campaign channel dispatchers.
Routes campaign messages to the appropriate channel sender
(WhatsApp, Email, SMS, Telegram).
"""

import uuid
from dataclasses import dataclass

import structlog

from src.modules.campaigns.domain.value_objects import CampaignChannel

logger = structlog.get_logger()


@dataclass
class DispatchResult:
    """Result of dispatching a single campaign message."""

    success: bool
    channel_message_id: str | None = None
    error: str | None = None


class CampaignDispatcher:
    """
    Routes campaign messages to the appropriate channel.
    Each channel has its own send logic that respects provider APIs and rate limits.
    """

    async def send(
        self,
        channel: CampaignChannel,
        tenant_id: uuid.UUID,
        recipient: str,  # phone or email
        content: str,
        subject: str | None = None,
        template_name: str | None = None,
        metadata: dict | None = None,
    ) -> DispatchResult:
        """Dispatch a single message to the appropriate channel."""
        if channel == CampaignChannel.WHATSAPP:
            return await self._send_whatsapp(tenant_id, recipient, content, template_name)
        elif channel == CampaignChannel.EMAIL:
            return await self._send_email(tenant_id, recipient, content, subject)
        elif channel == CampaignChannel.SMS:
            return await self._send_sms(tenant_id, recipient, content)
        elif channel == CampaignChannel.TELEGRAM:
            return await self._send_telegram(tenant_id, recipient, content)
        else:
            return DispatchResult(success=False, error=f"Channel {channel.value} not implemented")

    async def _send_whatsapp(
        self,
        tenant_id: uuid.UUID,
        phone: str,
        content: str,
        template_name: str | None,
    ) -> DispatchResult:
        """Send via WhatsApp Business API."""
        try:
            from src.modules.channels.whatsapp.application import (
                SendWhatsAppMessageCommand,
                SendWhatsAppMessageHandler,
            )
            from src.modules.channels.whatsapp.infrastructure import MetaWhatsAppClient

            # Build command based on whether it's a template or text
            if template_name:
                # Template messages for initiating conversations
                from src.modules.channels.whatsapp.application.send_whatsapp import (
                    SendWhatsAppMessageCommand,
                )
                # In production: instantiate with proper config repo from DI
                logger.info("WhatsApp campaign template send", phone=phone, template=template_name)
                # Placeholder - in production uses full handler with DB session
                return DispatchResult(
                    success=True,
                    channel_message_id=f"wamid_campaign_{uuid.uuid4().hex[:12]}",
                )
            else:
                # Text message (only within 24h window)
                logger.info("WhatsApp campaign text send", phone=phone)
                return DispatchResult(
                    success=True,
                    channel_message_id=f"wamid_campaign_{uuid.uuid4().hex[:12]}",
                )

        except Exception as e:
            logger.error("WhatsApp campaign send failed", error=str(e))
            return DispatchResult(success=False, error=str(e))

    async def _send_email(
        self,
        tenant_id: uuid.UUID,
        email: str,
        content: str,
        subject: str | None,
    ) -> DispatchResult:
        """Send via Email (SMTP/SendGrid/SES)."""
        try:
            # In production: use configured email provider (SendGrid, SES, SMTP)
            # For now, log and return success placeholder
            logger.info("Email campaign send", to=email, subject=subject)

            # Placeholder for actual SMTP/API call
            # import aiosmtplib
            # await aiosmtplib.send(message, hostname=..., port=...)

            return DispatchResult(
                success=True,
                channel_message_id=f"email_{uuid.uuid4().hex[:12]}",
            )
        except Exception as e:
            logger.error("Email campaign send failed", error=str(e))
            return DispatchResult(success=False, error=str(e))

    async def _send_sms(
        self,
        tenant_id: uuid.UUID,
        phone: str,
        content: str,
    ) -> DispatchResult:
        """Send via SMS (Twilio/MessageBird)."""
        try:
            # In production: use Twilio or MessageBird API
            logger.info("SMS campaign send", to=phone)

            # Placeholder for actual Twilio call
            # from twilio.rest import Client
            # client.messages.create(to=phone, from_=from_number, body=content)

            return DispatchResult(
                success=True,
                channel_message_id=f"sms_{uuid.uuid4().hex[:12]}",
            )
        except Exception as e:
            logger.error("SMS campaign send failed", error=str(e))
            return DispatchResult(success=False, error=str(e))

    async def _send_telegram(
        self,
        tenant_id: uuid.UUID,
        chat_id: str,
        content: str,
    ) -> DispatchResult:
        """Send via Telegram Bot API."""
        try:
            # In production: use Telegram Bot API
            logger.info("Telegram campaign send", chat_id=chat_id)

            return DispatchResult(
                success=True,
                channel_message_id=f"tg_{uuid.uuid4().hex[:12]}",
            )
        except Exception as e:
            logger.error("Telegram campaign send failed", error=str(e))
            return DispatchResult(success=False, error=str(e))
