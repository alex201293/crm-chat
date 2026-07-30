"""Repository interfaces for the Chat bounded context."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.chat.domain.entities.conversation import Conversation
from src.modules.chat.domain.entities.message import Message
from src.modules.chat.domain.value_objects.message_content import ConversationStatus


class IConversationRepository(ABC):
    """Port for conversation persistence."""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Persist a new conversation."""
        ...

    @abstractmethod
    async def get_by_id(
        self, conversation_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Conversation | None:
        """Find a conversation by ID within a tenant."""
        ...

    @abstractmethod
    async def get_by_external_id(
        self, external_id: str, tenant_id: uuid.UUID
    ) -> Conversation | None:
        """Find a conversation by external channel ID."""
        ...

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """Update an existing conversation."""
        ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: ConversationStatus | None = None,
        assigned_to: uuid.UUID | None = None,
        is_ai_handling: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Conversation]:
        """List conversations with filtering."""
        ...

    @abstractmethod
    async def count_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: ConversationStatus | None = None,
    ) -> int:
        """Count conversations matching criteria."""
        ...

    @abstractmethod
    async def get_pending_for_assignment(
        self, tenant_id: uuid.UUID, limit: int = 10
    ) -> list[Conversation]:
        """Get unassigned pending conversations (for agent queue)."""
        ...


class IMessageRepository(ABC):
    """Port for message persistence."""

    @abstractmethod
    async def create(self, message: Message) -> Message:
        """Persist a new message."""
        ...

    @abstractmethod
    async def get_by_conversation(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[Message]:
        """Get messages for a conversation (paginated, newest first)."""
        ...

    @abstractmethod
    async def get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        """
        Get conversation history formatted for AI context.
        Returns [{"role": "user"|"assistant", "content": "..."}]
        """
        ...

    @abstractmethod
    async def count_by_conversation(
        self, conversation_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        """Count messages in a conversation."""
        ...
