"""Pydantic schemas for CRM API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# Contact Schemas
# =============================================================================
class CreateContactRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=20)
    company_id: str | None = None
    source: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None
    custom_fields: dict | None = None


class UpdateContactRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=20)
    company_id: str | None = None
    lifecycle_stage: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    country: str | None = Field(default=None, max_length=2)
    city: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=10)


class ContactResponse(BaseModel):
    id: str
    full_name: str
    email: str | None
    phone: str | None
    company_id: str | None
    lifecycle_stage: str
    tags: list[str]
    source: str | None
    total_conversations: int
    total_messages: int
    last_seen_at: str | None
    created_at: str


# =============================================================================
# Company Schemas
# =============================================================================
class CreateCompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=2)


class CompanyResponse(BaseModel):
    id: str
    name: str
    domain: str | None
    industry: str | None
    size: str | None
    website: str | None
    country: str | None
    created_at: str


# =============================================================================
# Deal Schemas
# =============================================================================
class CreateDealRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    pipeline_id: str | None = None
    stage_id: str | None = None
    value: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", max_length=3)
    contact_id: str | None = None
    company_id: str | None = None
    assigned_to_id: str | None = None
    expected_close_date: str | None = None


class MoveDealStageRequest(BaseModel):
    stage_id: str


class LoseDealRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DealResponse(BaseModel):
    id: str
    pipeline_id: str
    stage_id: str | None
    title: str
    value: int
    currency: str
    probability: int
    status: str
    contact_id: str | None
    company_id: str | None
    assigned_to_id: str | None
    expected_close_date: str | None
    won_at: str | None
    lost_at: str | None
    lost_reason: str | None
    tags: list[str]
    created_at: str


# =============================================================================
# Pipeline Schemas
# =============================================================================
class StageResponse(BaseModel):
    id: str
    name: str
    color: str
    order: int
    is_won: bool
    is_lost: bool
    probability: int


class PipelineResponse(BaseModel):
    id: str
    name: str
    is_default: bool
    is_active: bool
    stages: list[StageResponse]


# =============================================================================
# Task Schemas
# =============================================================================
class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to_id: str | None = None
    contact_id: str | None = None
    deal_id: str | None = None
    due_date: str | None = None
    priority: str = Field(default="normal")


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    status: str
    priority: str
    assigned_to_id: str | None
    contact_id: str | None
    deal_id: str | None
    due_date: str | None
    completed_at: str | None
    created_at: str


# =============================================================================
# Note Schemas
# =============================================================================
class CreateNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    contact_id: str | None = None
    deal_id: str | None = None


class NoteResponse(BaseModel):
    id: str
    content: str
    is_pinned: bool
    author_id: str | None
    contact_id: str | None
    deal_id: str | None
    created_at: str


# =============================================================================
# Activity Schemas
# =============================================================================
class ActivityResponse(BaseModel):
    id: str
    activity_type: str
    title: str
    description: str | None
    user_id: str | None
    created_at: str


# =============================================================================
# Generic
# =============================================================================
class PaginatedResponse(BaseModel):
    data: list
    total: int
    page: int
    page_size: int
