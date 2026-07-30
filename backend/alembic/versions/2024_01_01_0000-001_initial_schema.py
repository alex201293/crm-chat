"""Initial schema - tenants, users, roles, conversations, contacts, CRM

Revision ID: 001
Revises: None
Create Date: 2024-01-01 00:00:00.000000+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""

    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # --- TENANTS ---
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("domain", sa.String(255), unique=True, nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("plan", sa.String(50), nullable=False,
                  server_default="free"),
        sa.Column("settings", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False,
                  server_default="true"),
        sa.Column("max_users", sa.Integer, nullable=False,
                  server_default="5"),
        sa.Column("max_conversations_per_month", sa.Integer,
                  nullable=False, server_default="1000"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True),
                  nullable=True),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # --- PERMISSIONS ---
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("code", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("module", sa.String(50), nullable=False),
    )

    # --- ROLES ---
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.UniqueConstraint("name", "tenant_id",
                           name="uq_role_name_tenant"),
    )

    # --- USERS ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False,
                  server_default="true"),
        sa.Column("is_verified", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("mfa_secret", sa.String(100), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("preferences", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("google_id", sa.String(100), nullable=True),
        sa.Column("microsoft_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.UniqueConstraint("email", "tenant_id",
                           name="uq_user_email_tenant"),
    )
    op.create_index("ix_users_tenant_email", "users",
                    ["tenant_id", "email"])
    op.create_index("ix_users_tenant_active", "users",
                    ["tenant_id", "is_active"])
    op.create_index("ix_users_google_id", "users", ["google_id"])
    op.create_index("ix_users_microsoft_id", "users", ["microsoft_id"])

    # --- USER ROLES ---
    op.create_table(
        "user_roles",
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("role_id", UUID(as_uuid=True),
                  sa.ForeignKey("roles.id", ondelete="CASCADE"),
                  primary_key=True),
    )

    # --- ROLE PERMISSIONS ---
    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUID(as_uuid=True),
                  sa.ForeignKey("roles.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("permission_id", UUID(as_uuid=True),
                  sa.ForeignKey("permissions.id", ondelete="CASCADE"),
                  primary_key=True),
    )

    # --- REFRESH TOKENS ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("token_hash", sa.String(255), unique=True,
                  nullable=False),
        sa.Column("device_info", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column("is_revoked", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
    )
    op.create_index("ix_refresh_tokens_user_active",
                    "refresh_tokens", ["user_id", "is_revoked"])
    op.create_index("ix_refresh_tokens_expires",
                    "refresh_tokens", ["expires_at"])

    # --- AUDIT LOGS ---
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_tenant_created",
                    "audit_logs", ["tenant_id", "created_at"])
    op.create_index("ix_audit_logs_user_action",
                    "audit_logs", ["user_id", "action"])

    # --- COMPANIES ---
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("annual_revenue", sa.Integer, nullable=True),
        sa.Column("custom_fields", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True),
                  nullable=True),
    )
    op.create_index("ix_companies_tenant_name", "companies",
                    ["tenant_id", "name"])

    # --- CONTACTS ---
    op.create_table(
        "contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("company_id", UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("language", sa.String(10), nullable=True,
                  server_default="es"),
        sa.Column("whatsapp_id", sa.String(20), nullable=True),
        sa.Column("telegram_id", sa.String(50), nullable=True),
        sa.Column("facebook_id", sa.String(50), nullable=True),
        sa.Column("instagram_id", sa.String(50), nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_fields", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("lifecycle_stage", sa.String(50), nullable=False,
                  server_default="subscriber"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("total_conversations", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("total_messages", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("email_opted_in", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("sms_opted_in", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("whatsapp_opted_in", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True),
                  nullable=True),
    )
    op.create_index("ix_contacts_tenant_email", "contacts",
                    ["tenant_id", "email"])
    op.create_index("ix_contacts_tenant_phone", "contacts",
                    ["tenant_id", "phone"])
    op.create_index("ix_contacts_tenant_name", "contacts",
                    ["tenant_id", "full_name"])
    op.create_index("ix_contacts_external", "contacts",
                    ["tenant_id", "external_id"])
    op.create_index("ix_contacts_whatsapp", "contacts",
                    ["whatsapp_id"])
    op.create_index("ix_contacts_telegram", "contacts",
                    ["telegram_id"])

    # --- CONVERSATIONS ---
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("contact_id", UUID(as_uuid=True),
                  sa.ForeignKey("contacts.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("channel", sa.String(30), nullable=False,
                  server_default="web"),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="active"),
        sa.Column("priority", sa.String(20), nullable=False,
                  server_default="normal"),
        sa.Column("assigned_agent_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("is_ai_handling", sa.Boolean, nullable=False,
                  server_default="true"),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("last_message_preview", sa.String(200),
                  nullable=True),
        sa.Column("unread_count", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("message_count", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("first_response_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("ai_confidence_score", sa.Float, nullable=True),
        sa.Column("escalation_reason", sa.String(200), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("csat_score", sa.Integer, nullable=True),
        sa.Column("csat_comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
    )
    op.create_index("ix_conversations_tenant_status",
                    "conversations", ["tenant_id", "status"])
    op.create_index("ix_conversations_tenant_channel",
                    "conversations", ["tenant_id", "channel"])
    op.create_index("ix_conversations_tenant_assigned",
                    "conversations",
                    ["tenant_id", "assigned_agent_id"])
    op.create_index("ix_conversations_last_message",
                    "conversations",
                    ["tenant_id", "last_message_at"])
    op.create_index("ix_conversations_external",
                    "conversations", ["external_id"])

    # --- MESSAGES ---
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("conversation_id", UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id",
                               ondelete="CASCADE"),
                  nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("sender_id", UUID(as_uuid=True), nullable=True),
        sa.Column("sender_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(30), nullable=False,
                  server_default="text"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("attachments", JSONB, nullable=False,
                  server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="sent"),
        sa.Column("ai_generated", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("ai_model", sa.String(50), nullable=True),
        sa.Column("ai_tokens_used", sa.Integer, nullable=True),
        sa.Column("is_internal", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("metadata", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_conversation_created",
                    "messages",
                    ["conversation_id", "created_at"])
    op.create_index("ix_messages_tenant_created", "messages",
                    ["tenant_id", "created_at"])
    op.create_index("ix_messages_external", "messages",
                    ["external_id"])

    # --- CONVERSATION ASSIGNMENTS ---
    op.create_table(
        "conversation_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("conversation_id", UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id",
                               ondelete="CASCADE"),
                  nullable=False),
        sa.Column("assigned_from_id", UUID(as_uuid=True),
                  nullable=True),
        sa.Column("assigned_to_id", UUID(as_uuid=True),
                  nullable=True),
        sa.Column("assignment_type", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conv_assignments_conversation",
                    "conversation_assignments",
                    ["conversation_id", "assigned_at"])

    # --- PIPELINES ---
    op.create_table(
        "pipelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False,
                  server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
    )

    # --- PIPELINE STAGES ---
    op.create_table(
        "pipeline_stages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("pipeline_id", UUID(as_uuid=True),
                  sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=False,
                  server_default="#3B82F6"),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("is_won", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("is_lost", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("probability", sa.Integer, nullable=False,
                  server_default="0"),
    )
    op.create_index("ix_pipeline_stages_pipeline_order",
                    "pipeline_stages", ["pipeline_id", "order"])

    # --- DEALS ---
    op.create_table(
        "deals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("pipeline_id", UUID(as_uuid=True),
                  sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("stage_id", UUID(as_uuid=True),
                  sa.ForeignKey("pipeline_stages.id",
                               ondelete="SET NULL"),
                  nullable=True),
        sa.Column("contact_id", UUID(as_uuid=True),
                  sa.ForeignKey("contacts.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("company_id", UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("assigned_to_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("value", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False,
                  server_default="USD"),
        sa.Column("probability", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("expected_close_date", sa.Date, nullable=True),
        sa.Column("won_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("lost_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("lost_reason", sa.String(500), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_fields", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True),
                  nullable=True),
    )
    op.create_index("ix_deals_tenant_stage", "deals",
                    ["tenant_id", "stage_id"])
    op.create_index("ix_deals_tenant_assigned", "deals",
                    ["tenant_id", "assigned_to_id"])
    op.create_index("ix_deals_tenant_close_date", "deals",
                    ["tenant_id", "expected_close_date"])

    # --- TASKS ---
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("contact_id", UUID(as_uuid=True),
                  sa.ForeignKey("contacts.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("deal_id", UUID(as_uuid=True),
                  sa.ForeignKey("deals.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("assigned_to_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="pending"),
        sa.Column("priority", sa.String(20), nullable=False,
                  server_default="normal"),
        sa.Column("due_date", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
    )
    op.create_index("ix_tasks_tenant_assigned_due", "tasks",
                    ["tenant_id", "assigned_to_id", "due_date"])
    op.create_index("ix_tasks_tenant_status", "tasks",
                    ["tenant_id", "status"])

    # --- NOTES ---
    op.create_table(
        "notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("contact_id", UUID(as_uuid=True),
                  sa.ForeignKey("contacts.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("deal_id", UUID(as_uuid=True),
                  sa.ForeignKey("deals.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("author_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_pinned", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=True),
    )

    # --- ACTIVITIES ---
    op.create_table(
        "activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False,
                  index=True),
        sa.Column("contact_id", UUID(as_uuid=True),
                  sa.ForeignKey("contacts.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("deal_id", UUID(as_uuid=True),
                  sa.ForeignKey("deals.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activities_contact_created", "activities",
                    ["contact_id", "created_at"])
    op.create_index("ix_activities_deal_created", "activities",
                    ["deal_id", "created_at"])

    # --- ROW LEVEL SECURITY ---
    # Enable RLS on high-volume tables
    for table in ["conversations", "messages", "contacts",
                  "companies", "deals", "tasks", "notes",
                  "activities"]:
        op.execute(
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"
        )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    tables = [
        "activities", "notes", "tasks", "deals",
        "pipeline_stages", "pipelines",
        "conversation_assignments", "messages", "conversations",
        "contacts", "companies",
        "audit_logs", "refresh_tokens",
        "role_permissions", "user_roles",
        "users", "roles", "permissions", "tenants",
    ]
    for table in tables:
        op.drop_table(table)
