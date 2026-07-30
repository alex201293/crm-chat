"""
Chat REST API endpoints.
Manages conversations and messages via HTTP.
Real-time delivery handled via WebSocket (separate endpoint).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.api.dependencies import CurrentUser
from src.modules.chat.api.schemas import (
    AssignAgentRequest,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    MessagesListResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from src.modules.chat.application.commands import (
    AssignAgentCommand,
    AssignAgentHandler,
    CloseConversationCommand,
    CloseConversationHandler,
    CreateConversationCommand,
    CreateConversationHandler,
    ResolveConversationCommand,
    ResolveConversationHandler,
    SendMessageCommand,
    SendMessageHandler,
)
from src.modules.chat.application.queries import (
    ConversationListQuery,
    GetConversationsHandler,
    GetMessagesHandler,
    GetMessagesQuery,
)
from src.modules.chat.infrastructure.repositories import (
    ConversationRepository,
    MessageRepository,
)
from src.modules.chat.infrastructure.services import ws_manager
from src.modules.ai.application.services import AIService
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


# =============================================================================
# Conversations
# =============================================================================


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
)
async def list_conversations(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(default=None, pattern="^(active|pending|resolved|closed)$"),
    assigned_to: str | None = Query(default=None),
    is_ai_handling: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ConversationListResponse:
    """List conversations for the current tenant with optional filters."""
    handler = GetConversationsHandler(ConversationRepository(session))

    result = await handler.execute(
        ConversationListQuery(
            tenant_id=current_user.tenant_id,
            status=status,
            assigned_to=uuid.UUID(assigned_to) if assigned_to else None,
            is_ai_handling=is_ai_handling,
            page=page,
            page_size=page_size,
        )
    )

    return ConversationListResponse(
        data=[
            ConversationResponse(**c.__dict__)
            for c in result.conversations
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=201,
    summary="Create a conversation",
)
async def create_conversation(
    body: CreateConversationRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Start a new conversation."""
    handler = CreateConversationHandler(ConversationRepository(session))

    result = await handler.execute(
        CreateConversationCommand(
            tenant_id=current_user.tenant_id,
            contact_id=uuid.UUID(body.contact_id) if body.contact_id else None,
            channel=body.channel,
            subject=body.subject,
            external_id=body.external_id,
            metadata=body.metadata,
        )
    )

    return {
        "id": result.conversation_id,
        "contact_id": body.contact_id,
        "channel": result.channel,
        "status": result.status,
        "priority": "normal",
        "assigned_agent_id": None,
        "is_ai_handling": True,
        "subject": body.subject,
        "last_message_at": None,
        "last_message_preview": None,
        "unread_count": 0,
        "message_count": 0,
        "ai_confidence_score": None,
        "escalation_reason": None,
        "tags": [],
        "created_at": "",
    }


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessagesListResponse,
    summary="Get messages for a conversation",
)
async def get_messages(
    conversation_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> MessagesListResponse:
    """Get paginated messages for a conversation."""
    handler = GetMessagesHandler(MessageRepository(session))

    result = await handler.execute(
        GetMessagesQuery(
            tenant_id=current_user.tenant_id,
            conversation_id=uuid.UUID(conversation_id),
            page=page,
            page_size=page_size,
        )
    )

    return MessagesListResponse(
        data=[MessageResponse(**m.__dict__) for m in result.messages],
        total=result.total,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=201,
    summary="Send a message",
)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SendMessageResponse:
    """
    Send a message in a conversation.
    If the conversation is AI-handled, triggers an AI response.
    """
    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)

    # Determine sender type based on user role
    sender_type = "agent"

    handler = SendMessageHandler(
        conversation_repo=conv_repo,
        message_repo=msg_repo,
        ai_service=AIService(),
    )

    result = await handler.execute(
        SendMessageCommand(
            tenant_id=current_user.tenant_id,
            conversation_id=uuid.UUID(conversation_id),
            content=body.content,
            sender_type=sender_type,
            sender_id=current_user.id,
            sender_name=current_user.full_name,
            content_type=body.content_type,
            is_internal=body.is_internal,
        )
    )

    # Broadcast via WebSocket
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
        exclude=current_user.id,
    )

    # Build response
    message_resp = MessageResponse(
        id=result.message_id,
        conversation_id=result.conversation_id,
        sender_type=result.sender_type,
        sender_id=str(current_user.id),
        sender_name=result.sender_name,
        content_type=body.content_type,
        content=result.content,
        attachments=[],
        status="sent",
        ai_generated=False,
        ai_confidence=None,
        is_internal=body.is_internal,
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

        # Broadcast AI response via WebSocket
        await ws_manager.send_to_room(
            room=conversation_id,
            data={
                "event": "message:new",
                "data": {
                    "id": result.ai_response.message_id,
                    "conversation_id": conversation_id,
                    "content": result.ai_response.content,
                    "sender_type": result.ai_response.sender_type,
                    "sender_name": result.ai_response.sender_name,
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


@router.post(
    "/conversations/{conversation_id}/assign",
    summary="Assign an agent to a conversation",
)
async def assign_agent(
    conversation_id: str,
    body: AssignAgentRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Assign a human agent to a conversation."""
    handler = AssignAgentHandler(
        conversation_repo=ConversationRepository(session),
        message_repo=MessageRepository(session),
    )
    await handler.execute(
        AssignAgentCommand(
            tenant_id=current_user.tenant_id,
            conversation_id=uuid.UUID(conversation_id),
            agent_id=uuid.UUID(body.agent_id),
            agent_name=body.agent_name or current_user.full_name,
        )
    )

    # Notify via WebSocket
    await ws_manager.broadcast_to_tenant_agents(
        tenant_id=current_user.tenant_id,
        data={
            "event": "conversation:assigned",
            "data": {
                "conversation_id": conversation_id,
                "agent_id": body.agent_id,
            },
        },
    )

    return {"message": "Agent assigned successfully"}


@router.post(
    "/conversations/{conversation_id}/resolve",
    summary="Resolve a conversation",
)
async def resolve_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Mark a conversation as resolved."""
    handler = ResolveConversationHandler(ConversationRepository(session))
    await handler.execute(
        ResolveConversationCommand(
            tenant_id=current_user.tenant_id,
            conversation_id=uuid.UUID(conversation_id),
        )
    )
    return {"message": "Conversation resolved"}


@router.post(
    "/conversations/{conversation_id}/close",
    summary="Close a conversation",
)
async def close_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Permanently close a conversation."""
    handler = CloseConversationHandler(ConversationRepository(session))
    await handler.execute(
        CloseConversationCommand(
            tenant_id=current_user.tenant_id,
            conversation_id=uuid.UUID(conversation_id),
        )
    )
    return {"message": "Conversation closed"}
