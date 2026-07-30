"""Domain events for the Chat bounded context."""

import uuid

from src.shared.domain.base_entity import DomainEvent


class ConversationCreated(DomainEvent):
    """Emitted when a new conversation starts."""

    def __init__(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        channel: str,
        contact_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__()
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id
        self.channel = channel
        self.contact_id = contact_id


class MessageReceived(DomainEvent):
    """Emitted when a new message is received from a contact."""

    def __init__(
        self,
        message_id: uuid.UUID,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        content: str,
        sender_name: str,
        channel: str,
    ) -> None:
        super().__init__()
        self.message_id = message_id
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id
        self.content = content
        self.sender_name = sender_name
        self.channel = channel


class MessageSent(DomainEvent):
    """Emitted when a message is sent (by agent or AI)."""

    def __init__(
        self,
        message_id: uuid.UUID,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        sender_type: str,
        content: str,
    ) -> None:
        super().__init__()
        self.message_id = message_id
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id
        self.sender_type = sender_type
        self.content = content


class ConversationEscalated(DomainEvent):
    """Emitted when AI transfers conversation to human agent queue."""

    def __init__(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reason: str,
        reason_type: str,
    ) -> None:
        super().__init__()
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id
        self.reason = reason
        self.reason_type = reason_type


class ConversationAssigned(DomainEvent):
    """Emitted when a conversation is assigned to a human agent."""

    def __init__(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        assignment_type: str,  # "manual", "auto", "ai_to_agent"
    ) -> None:
        super().__init__()
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.assignment_type = assignment_type


class ConversationResolved(DomainEvent):
    """Emitted when a conversation is marked as resolved."""

    def __init__(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        super().__init__()
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id


class ConversationClosed(DomainEvent):
    """Emitted when a conversation is permanently closed."""

    def __init__(self, conversation_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        super().__init__()
        self.conversation_id = conversation_id
        self.tenant_id = tenant_id


class TypingIndicator(DomainEvent):
    """Emitted when someone starts/stops typing (real-time only, not persisted)."""

    def __init__(
        self,
        conversation_id: uuid.UUID,
        sender_type: str,
        sender_name: str,
        is_typing: bool,
    ) -> None:
        super().__init__()
        self.conversation_id = conversation_id
        self.sender_type = sender_type
        self.sender_name = sender_name
        self.is_typing = is_typing
