"""
WhatsApp Business API endpoints.
Handles Meta webhook verification/processing and management endpoints.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.api.dependencies import CurrentUser
from src.modules.channels.whatsapp.application import (
    HandleInboundMessageHandler,
    SendWhatsAppMessageCommand,
    SendWhatsAppMessageHandler,
)
from src.modules.channels.whatsapp.infrastructure import (
    MetaWhatsAppClient,
    get_phone_number_id_from_payload,
    parse_webhook_payload,
)
from src.modules.chat.infrastructure.repositories import (
    ConversationRepository,
    MessageRepository,
)
from src.modules.crm.infrastructure.repositories import ContactRepository
from src.modules.ai.application.services import AIService
from src.shared.infrastructure.database.session import get_db_session

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================
class SendMessageRequest(BaseModel):
    to: str = Field(min_length=10, max_length=20)
    text: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    media_caption: str | None = None
    media_filename: str | None = None
    buttons: list[dict] | None = None
    button_body: str | None = None
    list_body: str | None = None
    list_sections: list[dict] | None = None
    template_name: str | None = None
    template_language: str = "es"
    template_components: list[dict] | None = None


class ConfigRequest(BaseModel):
    phone_number_id: str = Field(min_length=1)
    business_account_id: str = Field(min_length=1)
    access_token: str = Field(min_length=1)
    verify_token: str = Field(min_length=1)
    phone_number: str = Field(min_length=10)
    display_name: str = Field(min_length=1, max_length=255)


class ConfigResponse(BaseModel):
    id: str
    phone_number_id: str
    phone_number: str
    display_name: str
    is_active: bool
    created_at: str


# =============================================================================
# Webhook Endpoints (Public - no auth, verified by Meta signature)
# =============================================================================


@router.get("/webhook", summary="WhatsApp webhook verification")
async def webhook_verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    """
    Meta webhook verification challenge.
    Returns hub.challenge if verify_token matches.
    """
    # In production, verify against stored verify_token per tenant
    # For now, accept if mode is "subscribe"
    if hub_mode == "subscribe" and hub_verify_token:
        logger.info("WhatsApp webhook verified", token=hub_verify_token[:8])
        return Response(content=hub_challenge, media_type="text/plain")

    return Response(status_code=403, content="Verification failed")


@router.post("/webhook", summary="WhatsApp webhook receiver")
async def webhook_receive(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """
    Receive and process WhatsApp webhook events from Meta.
    Processes messages asynchronously and returns 200 immediately.
    """
    payload = await request.json()

    # Parse the webhook payload
    messages, statuses = parse_webhook_payload(payload)

    if not messages and not statuses:
        return {"status": "ok"}

    # Resolve tenant by phone_number_id
    phone_number_id = get_phone_number_id_from_payload(payload)
    if not phone_number_id:
        logger.warning("No phone_number_id in webhook payload")
        return {"status": "ok"}

    # Load WhatsApp config for this phone number
    # In production, use IWhatsAppConfigRepository
    # For now, build config from the payload metadata
    from src.modules.channels.whatsapp.domain.entities import WhatsAppConfig
    from src.config.settings import get_settings

    settings = get_settings()
    # Simplified: in production, query DB for config by phone_number_id
    config = WhatsAppConfig(
        phone_number_id=phone_number_id,
        access_token=settings.app.APP_SECRET_KEY,  # Placeholder
        tenant_id=None,  # Resolved from DB in production
    )

    # Process inbound messages
    if messages:
        wa_client = MetaWhatsAppClient()
        handler = HandleInboundMessageHandler(
            whatsapp_client=wa_client,
            conversation_repo=ConversationRepository(session),
            message_repo=MessageRepository(session),
            contact_repo=ContactRepository(session),
            ai_service=AIService(),
        )

        for inbound in messages:
            try:
                await handler.execute(config, inbound)
            except Exception as e:
                logger.error(
                    "Error processing WhatsApp message",
                    message_id=inbound.message_id,
                    error=str(e),
                )

    # Process status updates (delivered, read, etc.)
    if statuses:
        for status in statuses:
            logger.debug(
                "WhatsApp status update",
                message_id=status.get("message_id"),
                status=status.get("status"),
            )
            # In production: update message delivery status in DB

    return {"status": "ok"}


# =============================================================================
# Management Endpoints (Authenticated)
# =============================================================================


@router.post("/send", summary="Send a WhatsApp message")
async def send_message(
    body: SendMessageRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Send a message to a WhatsApp number."""
    from src.modules.channels.whatsapp.domain.entities import WhatsAppConfig

    # In production: load config from DB via repository
    # Simplified placeholder
    config = WhatsAppConfig(tenant_id=current_user.tenant_id)

    wa_client = MetaWhatsAppClient()

    handler = SendWhatsAppMessageHandler(
        wa_client=wa_client,
        config_repo=_get_config_repo_placeholder(session),
    )

    result = await handler.execute(
        SendWhatsAppMessageCommand(
            tenant_id=current_user.tenant_id,
            to=body.to,
            text=body.text,
            media_url=body.media_url,
            media_type=body.media_type,
            media_caption=body.media_caption,
            media_filename=body.media_filename,
            buttons=body.buttons,
            button_body=body.button_body,
            list_body=body.list_body,
            list_sections=body.list_sections,
            template_name=body.template_name,
            template_language=body.template_language,
            template_components=body.template_components,
        )
    )

    if result.success:
        return {
            "success": True,
            "message_id": result.message_id,
        }
    return {
        "success": False,
        "error": result.error_message,
        "error_code": result.error_code,
    }


@router.post("/config", status_code=201, summary="Configure WhatsApp")
async def configure_whatsapp(
    body: ConfigRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConfigResponse:
    """Set up WhatsApp Business API credentials for the tenant."""
    from src.modules.channels.whatsapp.domain.entities import WhatsAppConfig

    config = WhatsAppConfig(
        tenant_id=current_user.tenant_id,
        phone_number_id=body.phone_number_id,
        business_account_id=body.business_account_id,
        access_token=body.access_token,
        verify_token=body.verify_token,
        phone_number=body.phone_number,
        display_name=body.display_name,
        is_active=True,
    )

    # In production: save via IWhatsAppConfigRepository
    # config_repo.create(config) or config_repo.update(config)
    logger.info(
        "WhatsApp configured",
        tenant_id=str(current_user.tenant_id),
        phone=body.phone_number,
    )

    return ConfigResponse(
        id=str(config.id),
        phone_number_id=config.phone_number_id,
        phone_number=config.phone_number,
        display_name=config.display_name,
        is_active=config.is_active,
        created_at=config.created_at.isoformat() if config.created_at else "",
    )


@router.get("/config", summary="Get WhatsApp configuration")
async def get_config(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Get the current WhatsApp configuration for the tenant."""
    # In production: load from DB
    return {
        "configured": False,
        "message": "WhatsApp not configured. Use POST /config to set up.",
    }


def _get_config_repo_placeholder(session):
    """
    Placeholder config repository.
    In production, use a proper SQLAlchemy implementation.
    """

    class InMemoryConfigRepo:
        async def get_by_tenant(self, tenant_id):
            from src.modules.channels.whatsapp.domain.entities import WhatsAppConfig
            from src.config.settings import get_settings

            settings = get_settings()
            # Return config from env vars if available
            token = getattr(settings, 'app', None)
            return WhatsAppConfig(
                tenant_id=tenant_id,
                phone_number_id="placeholder",
                access_token="placeholder",
                is_active=False,
            )

    return InMemoryConfigRepo()
