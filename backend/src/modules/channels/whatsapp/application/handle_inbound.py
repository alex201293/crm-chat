"""
Use case: Handle an inbound WhatsApp message.
Orchestrates: tenant resolution → contact resolution → conversation
routing → AI response → deliver reply back via WhatsApp.
"""

import uuid

import structlog

from src.modules.channels.whatsapp.domain.entities import WhatsAppConfig
from src.modules.channels.whatsapp.domain.interfaces import (
    IWhatsAppClient,
    InboundMessage,
    OutboundMessage,
)
from src.modules.channels.whatsapp.domain.value_objects import (
    WhatsAppMessageType,
)
from src.modules.chat.application.commands import (
    CreateConversationCommand,
    CreateConversationHandler,
    SendMessageCommand,
    SendMessageHandler,
)
from src.modules.chat.domain.interfaces.conversation_repository import (
    IConversationRepository,
    IMessageRepository,
)
from src.modules.crm.domain.entities.contact import Contact
from src.modules.crm.domain.interfaces.repositories import IContactRepository
from src.modules.ai.application.services.ai_service import AIService

logger = structlog.get_logger()


class HandleInboundMessageHandler:
    """
    Full pipeline for processing an inbound WhatsApp message:
    1. Resolve or create contact by phone number
    2. Find or create conversation (by WhatsApp external ID)
    3. Store the message via Chat module
    4. Trigger AI response (if AI-handled)
    5. Send AI reply back via WhatsApp
    """

    def __init__(
        self,
        whatsapp_client: IWhatsAppClient,
        conversation_repo: IConversationRepository,
        message_repo: IMessageRepository,
        contact_repo: IContactRepository,
        ai_service: AIService | None = None,
    ) -> None:
        self._wa_client = whatsapp_client
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._contact_repo = contact_repo
        self._ai_service = ai_service

    async def execute(
        self,
        config: WhatsAppConfig,
        inbound: InboundMessage,
    ) -> None:
        tenant_id = config.tenant_id
        if not tenant_id:
            logger.error("WhatsApp config missing tenant_id")
            return

        # 1. Mark as read (blue ticks)
        await self._wa_client.mark_as_read(config, inbound.message_id)

        # 2. Resolve or create contact
        contact = await self._resolve_contact(
            tenant_id=tenant_id,
            phone=inbound.from_number,
            name=inbound.profile_name,
        )

        # 3. Find or create conversation
        external_id = f"wa_{inbound.from_number}"
        conversation = await self._conversation_repo.get_by_external_id(
            external_id, tenant_id
        )

        if not conversation or not conversation.is_open:
            # Create new conversation
            create_handler = CreateConversationHandler(self._conversation_repo)
            result = await create_handler.execute(
                CreateConversationCommand(
                    tenant_id=tenant_id,
                    contact_id=contact.id if contact else None,
                    channel="whatsapp",
                    external_id=external_id,
                    metadata={
                        "whatsapp_number": inbound.from_number,
                        "profile_name": inbound.profile_name,
                    },
                )
            )
            conversation = await self._conversation_repo.get_by_id(
                uuid.UUID(result.conversation_id), tenant_id
            )

        if not conversation:
            logger.error("Failed to create conversation for WhatsApp")
            return

        # 4. Determine message content
        content = inbound.text or ""
        content_type = "text"

        if inbound.media:
            content_type = inbound.message_type.value
            if not content and inbound.media.caption:
                content = inbound.media.caption
            elif not content:
                content = f"[{inbound.message_type.value}]"

        # 5. Store message via Chat module
        send_handler = SendMessageHandler(
            conversation_repo=self._conversation_repo,
            message_repo=self._message_repo,
            ai_service=self._ai_service,
        )

        result = await send_handler.execute(
            SendMessageCommand(
                tenant_id=tenant_id,
                conversation_id=conversation.id,
                content=content,
                sender_type="user",
                sender_id=contact.id if contact else None,
                sender_name=inbound.profile_name or inbound.from_number,
                content_type=content_type,
            )
        )

        # 6. If AI generated a response, send it back via WhatsApp
        if result.ai_response and result.ai_response.content:
            await self._send_reply(
                config=config,
                to=inbound.from_number,
                text=result.ai_response.content,
            )

        # 7. If escalated, send escalation notice
        if result.escalated:
            await self._send_reply(
                config=config,
                to=inbound.from_number,
                text="Un agente humano te atenderá en breve. Por favor espera un momento.",
            )

        logger.info(
            "WhatsApp inbound processed",
            from_number=inbound.from_number,
            conversation_id=str(conversation.id),
            ai_responded=bool(result.ai_response),
            escalated=result.escalated,
        )

    async def _resolve_contact(
        self,
        tenant_id: uuid.UUID,
        phone: str,
        name: str | None,
    ) -> Contact | None:
        """Find existing contact by phone or create a new one."""
        contact = await self._contact_repo.get_by_phone(phone, tenant_id)
        if contact:
            # Update last seen
            contact.record_activity()
            contact.increment_messages()
            await self._contact_repo.update(contact)
            return contact

        # Create new contact
        display_name = name or phone
        new_contact = Contact.create(
            tenant_id=tenant_id,
            full_name=display_name,
            phone=phone,
            source="whatsapp",
        )
        new_contact.whatsapp_id = phone
        new_contact.whatsapp_opted_in = True
        await self._contact_repo.create(new_contact)
        return new_contact

    async def _send_reply(
        self, config: WhatsAppConfig, to: str, text: str
    ) -> None:
        """Send a text reply via WhatsApp."""
        message = OutboundMessage(
            to=to,
            message_type=WhatsAppMessageType.TEXT,
            text=text,
        )
        result = await self._wa_client.send_message(config, message)
        if not result.success:
            logger.error(
                "Failed to send WhatsApp reply",
                to=to,
                error=result.error_message,
            )
