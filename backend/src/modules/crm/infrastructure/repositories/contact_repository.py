"""SQLAlchemy implementation of IContactRepository."""

import uuid

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities.contact import Contact
from src.modules.crm.domain.interfaces.repositories import IContactRepository
from src.modules.crm.domain.value_objects import LifecycleStage
from src.modules.crm.infrastructure.models import ContactModel


class ContactRepository(IContactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, contact: Contact) -> Contact:
        model = ContactModel(
            id=contact.id,
            tenant_id=contact.tenant_id,
            company_id=contact.company_id,
            full_name=contact.full_name,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone=contact.phone,
            avatar_url=contact.avatar_url,
            country=contact.country,
            city=contact.city,
            timezone=contact.timezone,
            language=contact.language,
            whatsapp_id=contact.whatsapp_id,
            telegram_id=contact.telegram_id,
            facebook_id=contact.facebook_id,
            instagram_id=contact.instagram_id,
            external_id=contact.external_id,
            tags=contact.tags,
            custom_fields=contact.custom_fields,
            source=contact.source,
            utm_source=contact.utm_source,
            utm_medium=contact.utm_medium,
            utm_campaign=contact.utm_campaign,
            lifecycle_stage=contact.lifecycle_stage.value,
            last_seen_at=contact.last_seen_at,
            total_conversations=contact.total_conversations,
            total_messages=contact.total_messages,
            email_opted_in=contact.email_opted_in,
            sms_opted_in=contact.sms_opted_in,
            whatsapp_opted_in=contact.whatsapp_opted_in,
        )
        self._session.add(model)
        await self._session.flush()
        return contact

    async def get_by_id(
        self, contact_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Contact | None:
        stmt = select(ContactModel).where(
            ContactModel.id == contact_id,
            ContactModel.tenant_id == tenant_id,
            ContactModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(
        self, email: str, tenant_id: uuid.UUID
    ) -> Contact | None:
        stmt = select(ContactModel).where(
            ContactModel.email == email.lower(),
            ContactModel.tenant_id == tenant_id,
            ContactModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_phone(
        self, phone: str, tenant_id: uuid.UUID
    ) -> Contact | None:
        stmt = select(ContactModel).where(
            ContactModel.phone == phone,
            ContactModel.tenant_id == tenant_id,
            ContactModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, contact: Contact) -> Contact:
        stmt = select(ContactModel).where(ContactModel.id == contact.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Contact {contact.id} not found")

        model.company_id = contact.company_id
        model.full_name = contact.full_name
        model.first_name = contact.first_name
        model.last_name = contact.last_name
        model.email = contact.email
        model.phone = contact.phone
        model.avatar_url = contact.avatar_url
        model.country = contact.country
        model.city = contact.city
        model.timezone = contact.timezone
        model.language = contact.language
        model.whatsapp_id = contact.whatsapp_id
        model.telegram_id = contact.telegram_id
        model.facebook_id = contact.facebook_id
        model.instagram_id = contact.instagram_id
        model.tags = contact.tags
        model.custom_fields = contact.custom_fields
        model.lifecycle_stage = contact.lifecycle_stage.value
        model.last_seen_at = contact.last_seen_at
        model.total_conversations = contact.total_conversations
        model.total_messages = contact.total_messages
        model.email_opted_in = contact.email_opted_in
        model.sms_opted_in = contact.sms_opted_in
        model.whatsapp_opted_in = contact.whatsapp_opted_in

        await self._session.flush()
        return contact

    async def delete(
        self, contact_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        from datetime import datetime

        stmt = select(ContactModel).where(
            ContactModel.id == contact_id,
            ContactModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.deleted_at = datetime.utcnow()
            await self._session.flush()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        search: str | None = None,
        lifecycle_stage: LifecycleStage | None = None,
        tags: list[str] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Contact]:
        stmt = select(ContactModel).where(
            ContactModel.tenant_id == tenant_id,
            ContactModel.deleted_at.is_(None),
        )

        if search:
            search_filter = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ContactModel.full_name.ilike(search_filter),
                    ContactModel.email.ilike(search_filter),
                    ContactModel.phone.ilike(search_filter),
                )
            )

        if lifecycle_stage:
            stmt = stmt.where(
                ContactModel.lifecycle_stage == lifecycle_stage.value
            )

        if tags:
            # JSONB contains check for tags
            for tag in tags:
                stmt = stmt.where(
                    ContactModel.tags.contains([tag])
                )

        stmt = (
            stmt.order_by(ContactModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count(ContactModel.id)).where(
            ContactModel.tenant_id == tenant_id,
            ContactModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _to_entity(self, model: ContactModel) -> Contact:
        return Contact(
            id=model.id,
            tenant_id=model.tenant_id,
            company_id=model.company_id,
            full_name=model.full_name,
            first_name=model.first_name,
            last_name=model.last_name,
            email=model.email,
            phone=model.phone,
            avatar_url=model.avatar_url,
            country=model.country,
            city=model.city,
            timezone=model.timezone,
            language=model.language or "es",
            whatsapp_id=model.whatsapp_id,
            telegram_id=model.telegram_id,
            facebook_id=model.facebook_id,
            instagram_id=model.instagram_id,
            external_id=model.external_id,
            tags=model.tags or [],
            custom_fields=model.custom_fields or {},
            source=model.source,
            utm_source=model.utm_source,
            utm_medium=model.utm_medium,
            utm_campaign=model.utm_campaign,
            lifecycle_stage=LifecycleStage(model.lifecycle_stage),
            last_seen_at=model.last_seen_at,
            total_conversations=model.total_conversations,
            total_messages=model.total_messages,
            email_opted_in=model.email_opted_in,
            sms_opted_in=model.sms_opted_in,
            whatsapp_opted_in=model.whatsapp_opted_in,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
