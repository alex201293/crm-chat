"""
WebSocket endpoint for real-time chat.
Handles connection auth, message routing, typing indicators, and room management.
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.services.jwt_token_service import JWTTokenService
from src.modules.chat.application.commands import SendMessageCommand, SendMessageHandler
from src.modules.chat.infrastructure.repositories import (
    ConversationRepository,
    MessageRepository,
)
from src.modules.chat.infrastructure.services import ws_manager
from src.modules.ai.application.services import AIService
from src.shared.infrastructure.database.session import async_session_factory

logger = structlog.get_logger()

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
    tenant_id: str = Query(default=""),
):
    """
    WebSocket endpoint for real-time chat communication.

    Authentication: via query parameter `token` (JWT access token).
    Tenant: via query parameter `tenant_id`.

    Events received from client:
    - {"event": "join", "data": {"room": "<conversation_id>"}}
    - {"event": "leave", "data": {"room": "<conversation_id>"}}
    - {"event": "message", "data": {"conversation_id": "...", "content": "..."}}
    - {"event": "typing", "data": {"conversation_id": "...", "is_typing": true/false}}

    Events sent to client:
    - {"event": "message:new", "data": {...message_data}}
    - {"event": "agent:typing", "data": {"conversation_id": "...", "is_typing": ...}}
    - {"event": "conversation:updated", "data": {...}}
    - {"event": "conversation:assigned", "data": {...}}
    - {"event": "error", "data": {"message": "..."}}
    """

    # Authenticate
    user_payload = None
    if token:
        try:
            async with async_session_factory() as session:
                token_service = JWTTokenService(session)
                user_payload = token_service.decode_access_token(token)
        except Exception as e:
            logger.warning("WebSocket auth failed", error=str(e))
            await websocket.close(code=4001, reason="Authentication failed")
            return

    if not user_payload:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    # Connect
    client = await ws_manager.connect(
        websocket=websocket,
        user_id=user_payload.user_id,
        tenant_id=user_payload.tenant_id,
        user_type="agent",
        user_name=user_payload.email,
    )

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event", "")
            payload = data.get("data", {})

            if event == "join":
                room = payload.get("room", "")
                if room:
                    await ws_manager.join_room(user_payload.user_id, room)
                    await websocket.send_json({
                        "event": "joined",
                        "data": {"room": room},
                    })

            elif event == "leave":
                room = payload.get("room", "")
                if room:
                    await ws_manager.leave_room(user_payload.user_id, room)

            elif event == "message":
                conversation_id = payload.get("conversation_id", "")
                content = payload.get("content", "")
                sender_type = payload.get("sender_type", "agent")

                if conversation_id and content:
                    await _handle_incoming_message(
                        user_id=user_payload.user_id,
                        tenant_id=user_payload.tenant_id,
                        conversation_id=conversation_id,
                        content=content,
                        sender_type=sender_type,
                        sender_name=user_payload.email,
                    )

            elif event == "typing":
                conversation_id = payload.get("conversation_id", "")
                is_typing = payload.get("is_typing", False)
                if conversation_id:
                    await ws_manager.send_typing_indicator(
                        room=conversation_id,
                        sender_type="agent",
                        sender_name=user_payload.email,
                        is_typing=is_typing,
                        exclude=user_payload.user_id,
                    )

            elif event == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error", error=str(e), user_id=str(user_payload.user_id))
    finally:
        await ws_manager.disconnect(user_payload.user_id)


async def _handle_incoming_message(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    conversation_id: str,
    content: str,
    sender_type: str,
    sender_name: str,
) -> None:
    """Process a message received via WebSocket."""
    async with async_session_factory() as session:
        try:
            conv_repo = ConversationRepository(session)
            msg_repo = MessageRepository(session)

            handler = SendMessageHandler(
                conversation_repo=conv_repo,
                message_repo=msg_repo,
                ai_service=AIService() if sender_type == "user" else None,
            )

            result = await handler.execute(
                SendMessageCommand(
                    tenant_id=tenant_id,
                    conversation_id=uuid.UUID(conversation_id),
                    content=content,
                    sender_type=sender_type,
                    sender_id=user_id,
                    sender_name=sender_name,
                )
            )

            await session.commit()

            # Broadcast to room
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
                exclude=user_id,
            )

            # Broadcast AI response if present
            if result.ai_response:
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

            # Notify if escalated
            if result.escalated:
                await ws_manager.broadcast_to_tenant_agents(
                    tenant_id=tenant_id,
                    data={
                        "event": "conversation:escalated",
                        "data": {
                            "conversation_id": conversation_id,
                            "reason": result.escalation_reason,
                        },
                    },
                )

        except Exception as e:
            logger.error(
                "Error handling WebSocket message",
                error=str(e),
                conversation_id=conversation_id,
            )
            await ws_manager.send_to_user(
                user_id,
                {"event": "error", "data": {"message": "Failed to process message"}},
            )
