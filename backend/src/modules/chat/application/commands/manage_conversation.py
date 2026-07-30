"""
Use cases for conversation lifecycle management.
Create, assign, escalate, resolve, close conversations.
"""

import uuid
from dataclasses import dataclass

from src.modules.chat.domain.entities.conversation import Conversation
from src.modules.chat.domain.entities.message import Message
from src.modules.chat.domain.events.chat_events import ConversationAssigned
from src.modules.chat.domain.interfaces.conversation_repository import (
    IConversationRepository,
    IMessageRepository,
)
from src.modules.chat.domain.value_objects.message_content import (
    Channel,
    ConversationStatus,
    EscalationReason,
)
from src.shared.api.exceptions import EntityNotFoundError, ValidationError_
from src.shared.domain.events import event_bus


# =============================================================================
# Create Conversation
# =============================================================================
@dataclass
class CreateConversationCommand:
    tenant_id: uuid.UUID
    contact_id: uuid.UUID | None = None
    channel: str = "web"
    subject: str | None = None
    external_id: str | None = None
    metadata: dict | None = None


@dataclass
class CreateConversationResult:
    conversation_id: str
    channel: str
    status: str


class CreateConversationHandler:
    """Create a new conversation (e.g., when a contact initiates chat)."""

    def __init__(self, conversation_repo: IConversationRepository) -> None:
        self._conversation_repo = conversation_repo

    async def execute(self, command: CreateConversationCommand) -> CreateConversationResult:
        # Check if there's already an active conversation for this external_id
        if command.external_id:
            existing = await self._conversation_repo.get_by_external_id(
                command.external_id, command.tenant_id
            )
            if existing and existing.is_open:
                return CreateConversationResult(
                    conversation_id=str(existing.id),
                    channel=existing.channel.value,
                    status=existing.status.value,
                )

        channel = Channel(command.channel)
        conversation = Conversation.create(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
            channel=channel,
            subject=command.subject,
            external_id=command.external_id,
            metadata=command.metadata,
        )
        await self._conversation_repo.create(conversation)
        await event_bus.publish_all(conversation.clear_domain_events())

        return CreateConversationResult(
            conversation_id=str(conversation.id),
            channel=conversation.channel.value,
            status=conversation.status.value,
        )


# =============================================================================
# Assign Agent
# =============================================================================
@dataclass
class AssignAgentCommand:
    tenant_id: uuid.UUID
    conversation_id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str


class AssignAgentHandler:
    """Assign a human agent to a conversation."""

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        message_repo: IMessageRepository,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo

    async def execute(self, command: AssignAgentCommand) -> None:
        conversation = await self._conversation_repo.get_by_id(
            command.conversation_id, command.tenant_id
        )
        if not conversation:
            raise EntityNotFoundError("Conversation", str(command.conversation_id))

        conversation.assign_agent(command.agent_id)
        await self._conversation_repo.update(conversation)

        # Add system message
        system_msg = Message.create_system_message(
            tenant_id=command.tenant_id,
            conversation_id=command.conversation_id,
            content=f"{command.agent_name} joined the conversation.",
        )
        await self._message_repo.create(system_msg)

        await event_bus.publish(
            ConversationAssigned(
                conversation_id=conversation.id,
                tenant_id=command.tenant_id,
                agent_id=command.agent_id,
                assignment_type="manual",
            )
        )


# =============================================================================
# Resolve Conversation
# =============================================================================
@dataclass
class ResolveConversationCommand:
    tenant_id: uuid.UUID
    conversation_id: uuid.UUID


class ResolveConversationHandler:
    """Mark a conversation as resolved."""

    def __init__(self, conversation_repo: IConversationRepository) -> None:
        self._conversation_repo = conversation_repo

    async def execute(self, command: ResolveConversationCommand) -> None:
        conversation = await self._conversation_repo.get_by_id(
            command.conversation_id, command.tenant_id
        )
        if not conversation:
            raise EntityNotFoundError("Conversation", str(command.conversation_id))

        conversation.resolve()
        await self._conversation_repo.update(conversation)
        await event_bus.publish_all(conversation.clear_domain_events())


# =============================================================================
# Close Conversation
# =============================================================================
@dataclass
class CloseConversationCommand:
    tenant_id: uuid.UUID
    conversation_id: uuid.UUID


class CloseConversationHandler:
    """Permanently close a conversation."""

    def __init__(self, conversation_repo: IConversationRepository) -> None:
        self._conversation_repo = conversation_repo

    async def execute(self, command: CloseConversationCommand) -> None:
        conversation = await self._conversation_repo.get_by_id(
            command.conversation_id, command.tenant_id
        )
        if not conversation:
            raise EntityNotFoundError("Conversation", str(command.conversation_id))

        conversation.close()
        await self._conversation_repo.update(conversation)
        await event_bus.publish_all(conversation.clear_domain_events())
