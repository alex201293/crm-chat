"""Contact aggregate root for the CRM module."""

import uuid
from datetime import datetime

from src.modules.crm.domain.events.crm_events import ContactCreated
from src.modules.crm.domain.value_objects import LifecycleStage
from src.shared.domain.base_entity import AggregateRoot


class Contact(AggregateRoot):
    """
    A person who interacts with the organization.
    Central entity in the CRM, linked to conversations, deals, and companies.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        full_name: str = "",
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        avatar_url: str | None = None,
        country: str | None = None,
        city: str | None = None,
        timezone: str | None = None,
        language: str = "es",
        whatsapp_id: str | None = None,
        telegram_id: str | None = None,
        facebook_id: str | None = None,
        instagram_id: str | None = None,
        external_id: str | None = None,
        tags: list[str] | None = None,
        custom_fields: dict | None = None,
        source: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        lifecycle_stage: LifecycleStage = LifecycleStage.SUBSCRIBER,
        last_seen_at: datetime | None = None,
        total_conversations: int = 0,
        total_messages: int = 0,
        email_opted_in: bool = False,
        sms_opted_in: bool = False,
        whatsapp_opted_in: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at, updated_at=updated_at)
        self.company_id = company_id
        self.full_name = full_name
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.avatar_url = avatar_url
        self.country = country
        self.city = city
        self.timezone = timezone
        self.language = language
        self.whatsapp_id = whatsapp_id
        self.telegram_id = telegram_id
        self.facebook_id = facebook_id
        self.instagram_id = instagram_id
        self.external_id = external_id
        self.tags = tags or []
        self.custom_fields = custom_fields or {}
        self.source = source
        self.utm_source = utm_source
        self.utm_medium = utm_medium
        self.utm_campaign = utm_campaign
        self.lifecycle_stage = lifecycle_stage
        self.last_seen_at = last_seen_at
        self.total_conversations = total_conversations
        self.total_messages = total_messages
        self.email_opted_in = email_opted_in
        self.sms_opted_in = sms_opted_in
        self.whatsapp_opted_in = whatsapp_opted_in

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        full_name: str,
        email: str | None = None,
        phone: str | None = None,
        source: str | None = None,
        company_id: uuid.UUID | None = None,
    ) -> "Contact":
        """Factory for creating a new contact."""
        parts = full_name.strip().split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else None

        contact = cls(
            tenant_id=tenant_id,
            full_name=full_name.strip(),
            first_name=first_name,
            last_name=last_name,
            email=email.lower().strip() if email else None,
            phone=phone,
            source=source,
            company_id=company_id,
            lifecycle_stage=LifecycleStage.LEAD if email or phone else LifecycleStage.SUBSCRIBER,
        )
        contact.add_domain_event(
            ContactCreated(contact_id=contact.id, tenant_id=tenant_id, email=email)
        )
        return contact

    def update_lifecycle(self, stage: LifecycleStage) -> None:
        """Progress contact through the lifecycle funnel."""
        self.lifecycle_stage = stage
        self.updated_at = datetime.utcnow()

    def record_activity(self) -> None:
        """Mark contact as recently active."""
        self.last_seen_at = datetime.utcnow()

    def increment_conversations(self) -> None:
        self.total_conversations += 1

    def increment_messages(self) -> None:
        self.total_messages += 1

    def add_tag(self, tag: str) -> None:
        normalized = tag.strip().lower()
        if normalized and normalized not in self.tags:
            self.tags.append(normalized)
            self.updated_at = datetime.utcnow()

    def remove_tag(self, tag: str) -> None:
        normalized = tag.strip().lower()
        if normalized in self.tags:
            self.tags.remove(normalized)
            self.updated_at = datetime.utcnow()

    def set_custom_field(self, key: str, value: object) -> None:
        self.custom_fields[key] = value
        self.updated_at = datetime.utcnow()
