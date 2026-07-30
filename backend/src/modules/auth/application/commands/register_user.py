"""
Use case: Register a new user and create their tenant.
This is the primary onboarding flow for new organizations.
"""

from dataclasses import dataclass

from slugify import slugify

from src.modules.auth.domain.entities.tenant import Tenant
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.interfaces.tenant_repository import ITenantRepository
from src.modules.auth.domain.interfaces.token_service import ITokenService, TokenPair
from src.modules.auth.domain.interfaces.user_repository import IUserRepository
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.password import PlainPassword
from src.modules.auth.infrastructure.services.jwt_token_service import JWTTokenService
from src.modules.auth.infrastructure.services.password_service import PasswordService
from src.shared.api.exceptions import EntityAlreadyExistsError, ValidationError_
from src.shared.domain.events import event_bus


@dataclass
class RegisterUserCommand:
    """Input data for user registration."""

    email: str
    password: str
    full_name: str
    company_name: str


@dataclass
class RegisterUserResult:
    """Output of successful registration."""

    user_id: str
    tenant_id: str
    email: str
    full_name: str
    tenant_name: str
    tokens: TokenPair


class RegisterUserHandler:
    """
    Orchestrates the registration flow:
    1. Validate input
    2. Check email uniqueness
    3. Create tenant
    4. Create user with owner role
    5. Generate tokens
    6. Publish domain events
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        tenant_repository: ITenantRepository,
        token_service: ITokenService,
        password_service: PasswordService,
    ) -> None:
        self._user_repo = user_repository
        self._tenant_repo = tenant_repository
        self._token_service = token_service
        self._password_service = password_service

    async def execute(self, command: RegisterUserCommand) -> RegisterUserResult:
        # 1. Validate value objects
        email = Email(command.email)
        plain_password = PlainPassword(command.password)

        if not command.full_name.strip():
            raise ValidationError_("Full name is required", field="full_name")

        if not command.company_name.strip():
            raise ValidationError_("Company name is required", field="company_name")

        # 2. Check email uniqueness (across all tenants for simplicity)
        existing_user = await self._user_repo.get_by_email_any_tenant(email)
        if existing_user:
            raise EntityAlreadyExistsError("User", "email", str(email))

        # 3. Create tenant
        slug = await self._generate_unique_slug(command.company_name)
        tenant = Tenant.create(name=command.company_name.strip(), slug=slug)
        await self._tenant_repo.create(tenant)

        # 4. Create user
        password_hash = self._password_service.hash(plain_password)
        user = User.create(
            tenant_id=tenant.id,
            email=email,
            password_hash=password_hash,
            full_name=command.full_name.strip(),
        )
        user.is_verified = False
        user.roles = ["owner"]
        await self._user_repo.create(user)

        # 5. Generate tokens
        tokens = self._token_service.create_token_pair(
            user_id=user.id,
            tenant_id=tenant.id,
            email=str(email),
            roles=user.roles,
            permissions=list(user.permissions),
        )

        # Store refresh token
        await self._token_service.store_refresh_token(
            user_id=user.id,
            token_hash=JWTTokenService.hash_token(tokens.refresh_token),
            device_info=None,
            ip_address=None,
            expires_at=tokens.refresh_token_expires_at,
        )

        # 6. Publish domain events
        await event_bus.publish_all(user.clear_domain_events())

        return RegisterUserResult(
            user_id=str(user.id),
            tenant_id=str(tenant.id),
            email=str(email),
            full_name=user.full_name,
            tenant_name=tenant.name,
            tokens=tokens,
        )

    async def _generate_unique_slug(self, company_name: str) -> str:
        """Generate a unique slug from company name."""
        base_slug = slugify(company_name, max_length=80)
        if not base_slug:
            base_slug = "company"

        slug = base_slug
        counter = 1
        while await self._tenant_repo.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug
