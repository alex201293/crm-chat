"""SQLAlchemy implementation of ICompanyRepository."""

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities.company import Company
from src.modules.crm.domain.interfaces.repositories import ICompanyRepository
from src.modules.crm.infrastructure.models import CompanyModel


class CompanyRepository(ICompanyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, company: Company) -> Company:
        model = CompanyModel(
            id=company.id,
            tenant_id=company.tenant_id,
            name=company.name,
            domain=company.domain,
            industry=company.industry,
            size=company.size,
            website=company.website,
            phone=company.phone,
            address=company.address,
            country=company.country,
            annual_revenue=company.annual_revenue,
            custom_fields=company.custom_fields,
        )
        self._session.add(model)
        await self._session.flush()
        return company

    async def get_by_id(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Company | None:
        stmt = select(CompanyModel).where(
            CompanyModel.id == company_id,
            CompanyModel.tenant_id == tenant_id,
            CompanyModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, company: Company) -> Company:
        stmt = select(CompanyModel).where(CompanyModel.id == company.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Company {company.id} not found")

        model.name = company.name
        model.domain = company.domain
        model.industry = company.industry
        model.size = company.size
        model.website = company.website
        model.phone = company.phone
        model.address = company.address
        model.country = company.country
        model.annual_revenue = company.annual_revenue
        model.custom_fields = company.custom_fields
        await self._session.flush()
        return company

    async def delete(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        stmt = select(CompanyModel).where(
            CompanyModel.id == company_id,
            CompanyModel.tenant_id == tenant_id,
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
        offset: int = 0,
        limit: int = 20,
    ) -> list[Company]:
        stmt = select(CompanyModel).where(
            CompanyModel.tenant_id == tenant_id,
            CompanyModel.deleted_at.is_(None),
        )
        if search:
            stmt = stmt.where(
                or_(
                    CompanyModel.name.ilike(f"%{search}%"),
                    CompanyModel.domain.ilike(f"%{search}%"),
                )
            )
        stmt = stmt.order_by(CompanyModel.name).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count(CompanyModel.id)).where(
            CompanyModel.tenant_id == tenant_id,
            CompanyModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _to_entity(self, model: CompanyModel) -> Company:
        return Company(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            domain=model.domain,
            industry=model.industry,
            size=model.size,
            website=model.website,
            phone=model.phone,
            address=model.address,
            country=model.country,
            annual_revenue=model.annual_revenue,
            custom_fields=model.custom_fields or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
