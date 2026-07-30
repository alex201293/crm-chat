"""Domain entities for the WhatsApp module."""

import uuid
from datetime import datetime

from src.modules.channels.whatsapp.domain.value_objects import (
    TemplateCategory,
    TemplateStatus,
)
from src.shared.domain.base_entity import BaseEntity


class WhatsAppConfig(BaseEntity):
    """
    Per-tenant WhatsApp Business configuration.
    Stores API credentials and phone number details.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        phone_number_id: str = "",
        business_account_id: str = "",
        access_token: str = "",  # Encrypted at rest
        verify_token: str = "",
        phone_number: str = "",
        display_name: str = "",
        is_active: bool = True,
        webhook_url: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.phone_number_id = phone_number_id
        self.business_account_id = business_account_id
        self.access_token = access_token
        self.verify_token = verify_token
        self.phone_number = phone_number
        self.display_name = display_name
        self.is_active = is_active
        self.webhook_url = webhook_url
        self.updated_at = updated_at


class WhatsAppTemplate(BaseEntity):
    """
    A WhatsApp message template (must be approved by Meta).
    Used for initiating conversations outside the 24-hour window.
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        name: str = "",
        language: str = "es",
        category: TemplateCategory = TemplateCategory.UTILITY,
        status: TemplateStatus = TemplateStatus.PENDING,
        components: list[dict] | None = None,
        meta_template_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, created_at=created_at)
        self.name = name
        self.language = language
        self.category = category
        self.status = status
        self.components = components or []
        self.meta_template_id = meta_template_id
        self.updated_at = updated_at

    @property
    def is_approved(self) -> bool:
        return self.status == TemplateStatus.APPROVED
