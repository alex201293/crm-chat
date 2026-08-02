"""
Use case: Send a message in a conversation.
Handles both user messages (triggers AI response) and agent messages.
"""

import uuid
from dataclasses import dataclass

import structlog

from src.modules.ai.application.services.ai_service import AIService
from src.modules.chat.domain.entities.message import Message
from src.modules.chat.domain.events.chat_events import MessageReceived, MessageSent
from src.modules.chat.domain.interfaces.conversation_repository import (
    IConversationRepository,
    IMessageRepository,
)
from src.modules.chat.domain.value_objects.message_content import (
    EscalationReason,
    MessageContentType,
    MessageSenderType,
)
from src.shared.api.exceptions import EntityNotFoundError
from src.shared.domain.events import event_bus

logger = structlog.get_logger()


@dataclass
class SendMessageCommand:
    """Input for sending a message."""

    tenant_id: uuid.UUID
    conversation_id: uuid.UUID
    content: str
    sender_type: str  # "user", "agent"
    sender_id: uuid.UUID | None = None
    sender_name: str = ""
    content_type: str = "text"
    is_internal: bool = False  # Internal notes (agent only)


@dataclass
class SendMessageResult:
    """Output of sending a message."""

    message_id: str
    conversation_id: str
    content: str
    sender_type: str
    sender_name: str
    created_at: str
    # AI response (if triggered)
    ai_response: "SendMessageResult | None" = None
    escalated: bool = False
    escalation_reason: str | None = None


class SendMessageHandler:
    """
    Orchestrates message sending:
    1. Validate conversation exists
    2. Create and persist message
    3. Update conversation metadata
    4. If user message + AI handling: generate AI response
    5. If AI confidence low: escalate to human
    6. Publish events for real-time delivery
    """

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        message_repo: IMessageRepository,
        ai_service: AIService | None = None,
        tenant_settings: dict | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._ai_service = ai_service
        self._tenant_settings = tenant_settings or {}

    async def execute(self, command: SendMessageCommand) -> SendMessageResult:
        # 1. Get conversation
        conversation = await self._conversation_repo.get_by_id(
            command.conversation_id, command.tenant_id
        )
        if not conversation:
            raise EntityNotFoundError("Conversation", str(command.conversation_id))

        # 2. Create message
        sender_type = MessageSenderType(command.sender_type)
        content_type = MessageContentType(command.content_type)

        if sender_type == MessageSenderType.USER:
            message = Message.create_user_message(
                tenant_id=command.tenant_id,
                conversation_id=command.conversation_id,
                sender_id=command.sender_id,
                sender_name=command.sender_name,
                content=command.content,
                content_type=content_type,
            )
        elif sender_type == MessageSenderType.AGENT:
            message = Message.create_agent_message(
                tenant_id=command.tenant_id,
                conversation_id=command.conversation_id,
                agent_id=command.sender_id or uuid.uuid4(),
                agent_name=command.sender_name,
                content=command.content,
                content_type=content_type,
                is_internal=command.is_internal,
            )
        else:
            message = Message.create_system_message(
                tenant_id=command.tenant_id,
                conversation_id=command.conversation_id,
                content=command.content,
            )

        await self._message_repo.create(message)

        # 3. Update conversation
        is_from_agent = sender_type in (MessageSenderType.AGENT, MessageSenderType.AI)
        conversation.record_message(preview=command.content, is_from_agent=is_from_agent)

        # If agent sends message → switch to human mode permanently
        if sender_type == MessageSenderType.AGENT:
            conversation.is_ai_handling = False
            if command.sender_id:
                conversation.assigned_agent_id = command.sender_id
            conversation.status = "active"

        await self._conversation_repo.update(conversation)

        # 4. Publish event
        if sender_type == MessageSenderType.USER:
            await event_bus.publish(
                MessageReceived(
                    message_id=message.id,
                    conversation_id=conversation.id,
                    tenant_id=command.tenant_id,
                    content=command.content,
                    sender_name=command.sender_name,
                    channel=conversation.channel.value,
                )
            )
        else:
            await event_bus.publish(
                MessageSent(
                    message_id=message.id,
                    conversation_id=conversation.id,
                    tenant_id=command.tenant_id,
                    sender_type=sender_type.value,
                    content=command.content,
                )
            )

        result = SendMessageResult(
            message_id=str(message.id),
            conversation_id=str(conversation.id),
            content=message.content,
            sender_type=message.sender_type.value,
            sender_name=message.sender_name,
            created_at=message.created_at.isoformat() if message.created_at else "",
        )

        # 5. Generate AI response if applicable
        if (
            sender_type == MessageSenderType.USER
            and conversation.is_ai_handling
            and self._ai_service
            and not command.is_internal
        ):
            ai_result = await self._generate_ai_response(
                conversation_id=command.conversation_id,
                tenant_id=command.tenant_id,
                user_message=command.content,
            )
            if ai_result:
                result.ai_response = ai_result
                result.escalated = ai_result.escalated
                result.escalation_reason = ai_result.escalation_reason

        return result

    async def _generate_ai_response(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_message: str,
    ) -> SendMessageResult | None:
        """Generate and store an AI response, enhanced with RAG context."""
        try:
            # Get conversation history for context
            history = await self._message_repo.get_conversation_history(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                limit=20,
            )

            # Build system prompt from tenant settings
            system_prompt = self._tenant_settings.get(
                "ai_system_prompt",
                "You are a helpful customer support assistant. "
                "Be concise, friendly, and professional. "
                "Answer in the same language as the user's message.",
            )

            # RAG: Search knowledge base for relevant context
            context_documents: list[str] = []
            try:
                # Try vector search first
                from src.modules.chat.application.commands.send_message_with_rag import (
                    KnowledgeRAGService,
                )

                if hasattr(self._conversation_repo, "_session"):
                    rag_service = KnowledgeRAGService(self._conversation_repo._session)
                    rag_context = await rag_service.retrieve_context(
                        tenant_id=tenant_id,
                        user_message=user_message,
                    )
                    if rag_context and rag_context.documents:
                        context_documents = rag_context.documents
            except Exception:
                pass

            # Fallback: load documents directly from file system if no vector results
            if not context_documents:
                try:
                    import os
                    import glob
                    docs_dir = f"./storage/knowledge/{tenant_id}"
                    if os.path.isdir(docs_dir):
                        for fpath in glob.glob(f"{docs_dir}/*")[:5]:
                            with open(fpath, "r", errors="ignore") as f:
                                content = f.read(3000)
                                if content.strip():
                                    context_documents.append(content)
                except Exception:
                    pass

            if context_documents:
                system_prompt += (
                    "\n\nTienes acceso a la base de conocimiento de la empresa. "
                    "Usa el contexto proporcionado para responder con precisión. "
                    "Si la respuesta está en el contexto, úsala."
                )


            # Generate response
            ai_result = await self._ai_service.generate_response(
                user_message=user_message,
                system_prompt=system_prompt,
                conversation_history=history,
                context_documents=context_documents,
            )

            # Check if escalation needed
            should_escalate = self._ai_service.should_escalate(
                confidence=ai_result.confidence_score,
                message_content=user_message,
            )

            if should_escalate:
                # Escalate instead of responding
                conversation = await self._conversation_repo.get_by_id(
                    conversation_id, tenant_id
                )
                if conversation:
                    reason = EscalationReason.low_confidence(ai_result.confidence_score)
                    if self._ai_service.should_escalate(1.0, user_message):
                        reason = EscalationReason.user_request()

                    conversation.escalate_to_human(reason)
                    await self._conversation_repo.update(conversation)

                    # Send system message about escalation
                    system_msg = Message.create_system_message(
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        content="Un agente humano te atenderá en breve. Por favor espera un momento.",
                    )
                    await self._message_repo.create(system_msg)

                    await event_bus.publish_all(conversation.clear_domain_events())

                    return SendMessageResult(
                        message_id=str(system_msg.id),
                        conversation_id=str(conversation_id),
                        content=system_msg.content,
                        sender_type="system",
                        sender_name="System",
                        created_at=system_msg.created_at.isoformat() if system_msg.created_at else "",
                        escalated=True,
                        escalation_reason=reason.description,
                    )

            # Store AI response
            ai_message = Message.create_ai_response(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                content=ai_result.content,
                model=ai_result.model,
                tokens_used=ai_result.tokens_used,
                confidence=ai_result.confidence_score,
            )
            await self._message_repo.create(ai_message)

            # Update conversation
            conversation = await self._conversation_repo.get_by_id(
                conversation_id, tenant_id
            )
            if conversation:
                conversation.record_message(preview=ai_result.content, is_from_agent=True)
                conversation.update_ai_confidence(ai_result.confidence_score)
                await self._conversation_repo.update(conversation)

            # Publish event
            await event_bus.publish(
                MessageSent(
                    message_id=ai_message.id,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    sender_type="ai",
                    content=ai_result.content,
                )
            )

            return SendMessageResult(
                message_id=str(ai_message.id),
                conversation_id=str(conversation_id),
                content=ai_result.content,
                sender_type="ai",
                sender_name="AI Assistant",
                created_at=ai_message.created_at.isoformat() if ai_message.created_at else "",
            )

        except Exception as e:
            logger.error(
                "AI response generation failed",
                conversation_id=str(conversation_id),
                error=str(e),
            )
            return None
