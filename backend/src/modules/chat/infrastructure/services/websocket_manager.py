"""
WebSocket connection manager.
Handles connection lifecycle, room-based messaging, and presence tracking.
Designed to scale with Redis Pub/Sub for multi-instance deployments.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


@dataclass
class ConnectedClient:
    """Represents a connected WebSocket client."""

    websocket: WebSocket
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    user_type: str  # "agent" or "contact"
    user_name: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    rooms: set[str] = field(default_factory=set)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time chat.

    Features:
    - Connection tracking by user and tenant
    - Room-based messaging (one room per conversation)
    - Presence tracking (who is online)
    - Broadcast to tenant agents
    - Direct messaging to specific users

    For multi-instance scaling, replace in-memory dicts with Redis Pub/Sub.
    """

    def __init__(self) -> None:
        # user_id → ConnectedClient
        self._connections: dict[str, ConnectedClient] = {}
        # room (conversation_id) → set of user_ids
        self._rooms: dict[str, set[str]] = defaultdict(set)
        # tenant_id → set of agent user_ids (for broadcasting)
        self._tenant_agents: dict[str, set[str]] = defaultdict(set)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_type: str = "agent",
        user_name: str = "",
    ) -> ConnectedClient:
        """Register a new WebSocket connection."""
        await websocket.accept()

        client = ConnectedClient(
            websocket=websocket,
            user_id=user_id,
            tenant_id=tenant_id,
            user_type=user_type,
            user_name=user_name,
        )

        user_key = str(user_id)
        self._connections[user_key] = client

        # Track agents by tenant for broadcasts
        if user_type == "agent":
            self._tenant_agents[str(tenant_id)].add(user_key)

        logger.info(
            "WebSocket connected",
            user_id=user_key,
            tenant_id=str(tenant_id),
            user_type=user_type,
        )

        return client

    async def disconnect(self, user_id: uuid.UUID) -> None:
        """Remove a WebSocket connection and clean up rooms."""
        user_key = str(user_id)
        client = self._connections.pop(user_key, None)

        if client:
            # Remove from all rooms
            for room in client.rooms:
                self._rooms[room].discard(user_key)
                if not self._rooms[room]:
                    del self._rooms[room]

            # Remove from tenant agents
            tenant_key = str(client.tenant_id)
            self._tenant_agents[tenant_key].discard(user_key)

            logger.info("WebSocket disconnected", user_id=user_key)

    async def join_room(self, user_id: uuid.UUID, room: str) -> None:
        """Add a user to a room (conversation)."""
        user_key = str(user_id)
        client = self._connections.get(user_key)
        if client:
            client.rooms.add(room)
            self._rooms[room].add(user_key)

    async def leave_room(self, user_id: uuid.UUID, room: str) -> None:
        """Remove a user from a room."""
        user_key = str(user_id)
        client = self._connections.get(user_key)
        if client:
            client.rooms.discard(room)
            self._rooms[room].discard(user_key)

    async def send_to_room(self, room: str, data: dict[str, Any], exclude: uuid.UUID | None = None) -> None:
        """Send a message to all users in a room (conversation)."""
        exclude_key = str(exclude) if exclude else None

        for user_key in list(self._rooms.get(room, set())):
            if user_key == exclude_key:
                continue
            client = self._connections.get(user_key)
            if client:
                try:
                    await client.websocket.send_json(data)
                except Exception:
                    # Client disconnected, clean up
                    await self.disconnect(client.user_id)

    async def send_to_user(self, user_id: uuid.UUID, data: dict[str, Any]) -> None:
        """Send a message directly to a specific user."""
        client = self._connections.get(str(user_id))
        if client:
            try:
                await client.websocket.send_json(data)
            except Exception:
                await self.disconnect(user_id)

    async def broadcast_to_tenant_agents(
        self, tenant_id: uuid.UUID, data: dict[str, Any], exclude: uuid.UUID | None = None
    ) -> None:
        """Broadcast a message to all connected agents of a tenant."""
        exclude_key = str(exclude) if exclude else None
        tenant_key = str(tenant_id)

        for user_key in list(self._tenant_agents.get(tenant_key, set())):
            if user_key == exclude_key:
                continue
            client = self._connections.get(user_key)
            if client:
                try:
                    await client.websocket.send_json(data)
                except Exception:
                    await self.disconnect(client.user_id)

    async def send_typing_indicator(
        self,
        room: str,
        sender_type: str,
        sender_name: str,
        is_typing: bool,
        exclude: uuid.UUID | None = None,
    ) -> None:
        """Send typing indicator to a room."""
        await self.send_to_room(
            room=room,
            data={
                "event": "agent:typing",
                "data": {
                    "conversation_id": room,
                    "sender_type": sender_type,
                    "sender_name": sender_name,
                    "is_typing": is_typing,
                },
            },
            exclude=exclude,
        )

    def get_online_agents(self, tenant_id: uuid.UUID) -> list[dict[str, str]]:
        """Get list of online agents for a tenant."""
        tenant_key = str(tenant_id)
        agents = []
        for user_key in self._tenant_agents.get(tenant_key, set()):
            client = self._connections.get(user_key)
            if client:
                agents.append({
                    "user_id": user_key,
                    "user_name": client.user_name,
                    "connected_at": client.connected_at.isoformat(),
                })
        return agents

    def get_room_members(self, room: str) -> list[str]:
        """Get user IDs in a room."""
        return list(self._rooms.get(room, set()))

    @property
    def total_connections(self) -> int:
        return len(self._connections)

    def is_user_online(self, user_id: uuid.UUID) -> bool:
        return str(user_id) in self._connections


# Singleton instance
ws_manager = WebSocketManager()
