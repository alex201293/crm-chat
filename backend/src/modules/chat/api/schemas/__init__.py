"""Chat API schemas for request/response validation."""

from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================

class CreateConversationRequest(BaseModel):
    channel: str = Field(default="web", pattern="^(web|whatsapp|email|telegram|facebook|instagram|sms)$")
    contact_id: str | None = None
    subject: str | None = Field(default=None, max_length=500)
    external_id: str | None = None
    metadata: dict | None = None


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    content_type: str = Field(default="text", pattern="^(text|image|file|audio|video)$")
    is_internal: bool = False


class AssignAgentRequest(BaseModel):
    agent_id: str
    agent_name: str = ""


class TypingRequest(BaseModel):
    is_typing: bool


# =============================================================================
# Response Schemas
# =============================================================================

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    sender_id: str | None
    sender_name: str
    content_type: str
    content: str
    attachments: list[dict] = []
    status: str
    ai_generated: bool
    ai_confidence: float | None = None
    is_internal: bool
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    contact_id: str | None
    channel: str
    status: str
    priority: str
    assigned_agent_id: str | None
    is_ai_handling: bool
    subject: str | None
    last_message_at: str | None
    last_message_preview: str | None
    unread_count: int
    message_count: int
    ai_confidence_score: float | None
    escalation_reason: str | None
    tags: list[str]
    created_at: str


class ConversationListResponse(BaseModel):
    data: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class MessagesListResponse(BaseModel):
    data: list[MessageResponse]
    total: int


class SendMessageResponse(BaseModel):
    message: MessageResponse
    ai_response: MessageResponse | None = None
    escalated: bool = False
    escalation_reason: str | None = None
