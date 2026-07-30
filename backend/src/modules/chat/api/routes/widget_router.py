"""
Widget-facing API endpoints.
These are the public endpoints that the embeddable widget uses.
Authentication is via API key (tenant identification) rather than JWT.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.chat.api.schemas import (
    CreateConversationRequest,
    MessageResponse,
    MessagesListResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from src.modules.chat.application.commands import (
    CreateConversationCommand,
    CreateConversationHandler,
    SendMessageCommand,
    SendMessageHandler,
)
from src.modules.chat.application.queries import (
    GetMessagesHandler,
    GetMessagesQuery,
)
from src.modules.chat.infrastructure.repositories import (
    ConversationRepository,
    MessageRepository,
)
from src.modules.chat.infrastructure.services import ws_manager
from src.modules.ai.application.services import AIService
from src.shared.api.exceptions import AuthenticationError
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


async def _resolve_tenant_from_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_db_session),
) -> uuid.UUID:
    """
    Resolve tenant from widget API key.
    In production, API keys are stored in a dedicated table.
    For now, the API key IS the tenant_id (development simplification).
    """
    try:
        tenant_id = uuid.UUID(x_api_key)
    except ValueError:
        raise AuthenticationError("Invalid API key")

    # In production: validate against api_keys table
    # stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == hash(x_api_key))
    return tenant_id


@router.post(
    "/conversations",
    status_code=201,
    summary="Start a widget conversation",
)
async def widget_create_conversation(
    body: CreateConversationRequest,
    request: Request,
    tenant_id: Annotated[uuid.UUID, Depends(_resolve_tenant_from_api_key)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Create a new conversation from the embeddable widget."""
    handler = CreateConversationHandler(ConversationRepository(session))

    # Add visitor metadata
    metadata = body.metadata or {}
    metadata["user_agent"] = request.headers.get("User-Agent", "")
    metadata["origin"] = request.headers.get("Origin", "")

    result = await handler.execute(
        CreateConversationCommand(
            tenant_id=tenant_id,
            contact_id=uuid.UUID(body.contact_id) if body.contact_id else None,
            channel="web",
            subject=body.subject,
            external_id=body.external_id,
            metadata=metadata,
        )
    )

    return {
        "conversation_id": result.conversation_id,
        "status": result.status,
    }


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=201,
    summary="Send a message from the widget",
)
async def widget_send_message(
    conversation_id: str,
    body: SendMessageRequest,
    tenant_id: Annotated[uuid.UUID, Depends(_resolve_tenant_from_api_key)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_visitor_id: str = Header(default="", alias="X-Visitor-ID"),
    x_visitor_name: str = Header(default="Visitor", alias="X-Visitor-Name"),
) -> SendMessageResponse:
    """
    Send a message from a widget visitor.
    Triggers AI response automatically if the conversation is AI-handled.
    """
    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)

    # Build AI service with tenant settings
    # In production, load tenant settings from DB
    ai_service = AIService()

    handler = SendMessageHandler(
        conversation_repo=conv_repo,
        message_repo=msg_repo,
        ai_service=ai_service,
    )

    visitor_id = uuid.UUID(x_visitor_id) if x_visitor_id else None

    result = await handler.execute(
        SendMessageCommand(
            tenant_id=tenant_id,
            conversation_id=uuid.UUID(conversation_id),
            content=body.content,
            sender_type="user",
            sender_id=visitor_id,
            sender_name=x_visitor_name,
            content_type=body.content_type,
        )
    )

    # Broadcast to room (agents watching)
    await ws_manager.send_to_room(
        room=conversation_id,
        data={
            "event": "message:new",
            "data": {
                "id": result.message_id,
                "conversation_id": result.conversation_id,
                "content": result.content,
                "sender_type": result.sender_type,
                "sender_name": result.sender_name,
                "created_at": result.created_at,
            },
        },
    )

    # Notify tenant agents of new conversation activity
    await ws_manager.broadcast_to_tenant_agents(
        tenant_id=tenant_id,
        data={
            "event": "conversation:updated",
            "data": {
                "conversation_id": conversation_id,
                "last_message": result.content,
                "sender_name": x_visitor_name,
            },
        },
    )

    # Build response
    message_resp = MessageResponse(
        id=result.message_id,
        conversation_id=result.conversation_id,
        sender_type=result.sender_type,
        sender_id=x_visitor_id or None,
        sender_name=result.sender_name,
        content_type=body.content_type,
        content=result.content,
        attachments=[],
        status="sent",
        ai_generated=False,
        ai_confidence=None,
        is_internal=False,
        created_at=result.created_at,
    )

    ai_resp = None
    if result.ai_response:
        ai_resp = MessageResponse(
            id=result.ai_response.message_id,
            conversation_id=result.ai_response.conversation_id,
            sender_type=result.ai_response.sender_type,
            sender_id=None,
            sender_name=result.ai_response.sender_name,
            content_type="text",
            content=result.ai_response.content,
            attachments=[],
            status="sent",
            ai_generated=True,
            ai_confidence=None,
            is_internal=False,
            created_at=result.ai_response.created_at,
        )

        # Broadcast AI response to widget via room
        await ws_manager.send_to_room(
            room=conversation_id,
            data={
                "event": "message:new",
                "data": {
                    "id": result.ai_response.message_id,
                    "conversation_id": conversation_id,
                    "content": result.ai_response.content,
                    "sender_type": "ai",
                    "sender_name": "AI Assistant",
                    "created_at": result.ai_response.created_at,
                },
            },
        )

    return SendMessageResponse(
        message=message_resp,
        ai_response=ai_resp,
        escalated=result.escalated,
        escalation_reason=result.escalation_reason,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessagesListResponse,
    summary="Get conversation messages (widget)",
)
async def widget_get_messages(
    conversation_id: str,
    tenant_id: Annotated[uuid.UUID, Depends(_resolve_tenant_from_api_key)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> MessagesListResponse:
    """Get messages for a widget conversation (excludes internal notes)."""
    handler = GetMessagesHandler(MessageRepository(session))

    result = await handler.execute(
        GetMessagesQuery(
            tenant_id=tenant_id,
            conversation_id=uuid.UUID(conversation_id),
            page=page,
            page_size=page_size,
        )
    )

    # Filter out internal messages for widget
    public_messages = [m for m in result.messages if not m.is_internal]

    return MessagesListResponse(
        data=[MessageResponse(**m.__dict__) for m in public_messages],
        total=len(public_messages),
    )
