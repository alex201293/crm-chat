"""Use cases for Contact CRUD operations."""

import uuid
from dataclasses import dataclass

from src.modules.crm.domain.entities.activity import Activity
from src.modules.crm.domain.entities.contact import Contact
from src.modules.crm.domain.interfaces.repositories import (
    IActivityRepository,
    IContactRepository,
)
from src.modules.crm.domain.value_objects import ActivityType, LifecycleStage
from src.shared.api.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    ValidationError_,
)
from src.shared.domain.events import event_bus


@dataclass
class CreateContactCommand:
    tenant_id: uuid.UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    company_id: uuid.UUID | None = None
    source: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class CreateContactHandler:
    def __init__(
        self,
        contact_repo: IContactRepository,
        activity_repo: IActivityRepository,
    ) -> None:
        self._contact_repo = contact_repo
        self._activity_repo = activity_repo

    async def execute(self, cmd: CreateContactCommand) -> Contact:
        if not cmd.full_name.strip():
            raise ValidationError_("Full name is required", "full_name")

        # Check for duplicates by email
        if cmd.email:
            existing = await self._contact_repo.get_by_email(
                cmd.email, cmd.tenant_id
            )
            if existing:
                raise EntityAlreadyExistsError(
                    "Contact", "email", cmd.email
                )

        contact = Contact.create(
            tenant_id=cmd.tenant_id,
            full_name=cmd.full_name,
            email=cmd.email,
            phone=cmd.phone,
            source=cmd.source,
            company_id=cmd.company_id,
        )

        if cmd.tags:
            for tag in cmd.tags:
                contact.add_tag(tag)

        if cmd.custom_fields:
            contact.custom_fields = cmd.custom_fields

        await self._contact_repo.create(contact)

        # Record activity
        activity = Activity.create(
            tenant_id=cmd.tenant_id,
            activity_type=ActivityType.CONTACT_CREATED,
            title=f"Contact created: {contact.full_name}",
            contact_id=contact.id,
        )
        await self._activity_repo.create(activity)

        # Publish events
        await event_bus.publish_all(contact.clear_domain_events())

        return contact


@dataclass
class UpdateContactCommand:
    tenant_id: uuid.UUID
    contact_id: uuid.UUID
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company_id: uuid.UUID | None = None
    lifecycle_stage: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    country: str | None = None
    city: str | None = None
    language: str | None = None


class UpdateContactHandler:
    def __init__(self, contact_repo: IContactRepository) -> None:
        self._contact_repo = contact_repo

    async def execute(self, cmd: UpdateContactCommand) -> Contact:
        contact = await self._contact_repo.get_by_id(
            cmd.contact_id, cmd.tenant_id
        )
        if not contact:
            raise EntityNotFoundError("Contact", str(cmd.contact_id))

        if cmd.full_name is not None:
            contact.full_name = cmd.full_name.strip()
        if cmd.email is not None:
            contact.email = cmd.email.lower().strip() if cmd.email else None
        if cmd.phone is not None:
            contact.phone = cmd.phone
        if cmd.company_id is not None:
            contact.company_id = cmd.company_id
        if cmd.lifecycle_stage is not None:
            contact.update_lifecycle(LifecycleStage(cmd.lifecycle_stage))
        if cmd.tags is not None:
            contact.tags = [t.strip().lower() for t in cmd.tags]
        if cmd.custom_fields is not None:
            contact.custom_fields = cmd.custom_fields
        if cmd.country is not None:
            contact.country = cmd.country
        if cmd.city is not None:
            contact.city = cmd.city
        if cmd.language is not None:
            contact.language = cmd.language

        await self._contact_repo.update(contact)
        return contact
