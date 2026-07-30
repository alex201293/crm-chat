"""
Auth API endpoints.
All authentication and user management routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.api.dependencies import CurrentUser, TokenData
from src.modules.auth.api.schemas import (
    AuthResponse,
    ConfirmResetPasswordRequest,
    DisableMFARequest,
    LoginRequest,
    MFASetupResponse,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RequestResetPasswordRequest,
    TokenResponse,
    UserProfileResponse,
    VerifyMFARequest,
)
from src.modules.auth.application.commands import (
    ConfirmPasswordResetCommand,
    ConfirmPasswordResetHandler,
    DisableMFACommand,
    DisableMFAHandler,
    EnableMFACommand,
    EnableMFAHandler,
    LoginUserCommand,
    LoginUserHandler,
    RefreshTokenCommand,
    RefreshTokenHandler,
    RegisterUserCommand,
    RegisterUserHandler,
    RequestPasswordResetCommand,
    RequestPasswordResetHandler,
    VerifyMFASetupCommand,
    VerifyMFASetupHandler,
)
from src.modules.auth.application.queries import GetCurrentUserHandler
from src.modules.auth.infrastructure.repositories import TenantRepository, UserRepository
from src.modules.auth.infrastructure.services import (
    JWTTokenService,
    MFAService,
    PasswordService,
)
from src.shared.infrastructure.database.session import get_db_session

router = APIRouter()


# ===========================================================================
# Dependency helpers for handlers
# ===========================================================================


def _get_password_service() -> PasswordService:
    return PasswordService()


def _get_mfa_service() -> MFAService:
    return MFAService()


# ===========================================================================
# Routes
# ===========================================================================


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    summary="Register a new user and organization",
)
async def register(
    body: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthResponse:
    """
    Create a new organization (tenant) and its first user (owner).
    Returns JWT tokens for immediate authentication.
    """
    handler = RegisterUserHandler(
        user_repository=UserRepository(session),
        tenant_repository=TenantRepository(session),
        token_service=JWTTokenService(session),
        password_service=_get_password_service(),
    )

    result = await handler.execute(
        RegisterUserCommand(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            company_name=body.company_name,
        )
    )

    return AuthResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=900,  # 15 minutes in seconds
        user=UserProfileResponse(
            id=result.user_id,
            tenant_id=result.tenant_id,
            email=result.email,
            full_name=result.full_name,
            avatar_url=None,
            phone=None,
            is_verified=False,
            mfa_enabled=False,
            roles=["owner"],
            permissions=[],
            tenant_name=result.tenant_name,
            created_at="",
        ),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate with email and password",
)
async def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthResponse:
    """
    Authenticate a user. If MFA is enabled and no code provided,
    returns mfa_required=true with no tokens.
    """
    handler = LoginUserHandler(
        user_repository=UserRepository(session),
        token_service=JWTTokenService(session),
        password_service=_get_password_service(),
        mfa_service=_get_mfa_service(),
    )

    ip_address = request.client.host if request.client else None

    result = await handler.execute(
        LoginUserCommand(
            email=body.email,
            password=body.password,
            mfa_code=body.mfa_code,
            ip_address=ip_address,
            device_info=request.headers.get("User-Agent"),
        )
    )

    if result.mfa_required:
        return AuthResponse(
            access_token="",
            refresh_token="",
            expires_in=0,
            mfa_required=True,
            user=UserProfileResponse(
                id=result.user_id,
                tenant_id=result.tenant_id,
                email=result.email,
                full_name=result.full_name,
                avatar_url=None,
                phone=None,
                is_verified=False,
                mfa_enabled=True,
                roles=result.roles,
                permissions=[],
                tenant_name=None,
                created_at="",
            ),
        )

    return AuthResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=900,
        user=UserProfileResponse(
            id=result.user_id,
            tenant_id=result.tenant_id,
            email=result.email,
            full_name=result.full_name,
            avatar_url=None,
            phone=None,
            is_verified=False,
            mfa_enabled=False,
            roles=result.roles,
            permissions=[],
            tenant_name=None,
            created_at="",
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new token pair.
    The old refresh token is revoked (rotation).
    """
    handler = RefreshTokenHandler(
        user_repository=UserRepository(session),
        token_service=JWTTokenService(session),
    )

    ip_address = request.client.host if request.client else None

    result = await handler.execute(
        RefreshTokenCommand(
            refresh_token=body.refresh_token,
            ip_address=ip_address,
            device_info=request.headers.get("User-Agent"),
        )
    )

    return TokenResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=900,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke tokens",
)
async def logout(
    token_data: TokenData,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Revoke all refresh tokens for the current user."""
    token_service = JWTTokenService(session)
    await token_service.revoke_all_user_tokens(token_data.user_id)
    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileResponse:
    """Get the authenticated user's full profile."""
    handler = GetCurrentUserHandler(user_repository=UserRepository(session))
    result = await handler.execute(current_user.id, current_user.tenant_id)

    return UserProfileResponse(
        id=result.id,
        tenant_id=result.tenant_id,
        email=result.email,
        full_name=result.full_name,
        avatar_url=result.avatar_url,
        phone=result.phone,
        is_verified=result.is_verified,
        mfa_enabled=result.mfa_enabled,
        roles=result.roles,
        permissions=result.permissions,
        tenant_name=result.tenant_name,
        created_at=result.created_at,
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
)
async def forgot_password(
    body: RequestResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """
    Request a password reset link.
    Always returns success to prevent email enumeration.
    """
    handler = RequestPasswordResetHandler(user_repository=UserRepository(session))
    await handler.execute(RequestPasswordResetCommand(email=body.email))
    return MessageResponse(
        message="If the email exists, a reset link has been sent"
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Confirm password reset",
)
async def reset_password(
    body: ConfirmResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Reset password using a valid reset token."""
    handler = ConfirmPasswordResetHandler(
        user_repository=UserRepository(session),
        password_service=_get_password_service(),
    )
    await handler.execute(
        ConfirmPasswordResetCommand(
            token=body.token,
            new_password=body.new_password,
        )
    )
    return MessageResponse(message="Password has been reset successfully")


@router.post(
    "/mfa/enable",
    response_model=MFASetupResponse,
    summary="Enable MFA (step 1: get secret)",
)
async def enable_mfa(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MFASetupResponse:
    """Generate a TOTP secret and provisioning URI for QR code."""
    handler = EnableMFAHandler(
        user_repository=UserRepository(session),
        mfa_service=_get_mfa_service(),
    )
    result = await handler.execute(
        EnableMFACommand(user_id=current_user.id, tenant_id=current_user.tenant_id)
    )
    return MFASetupResponse(
        secret=result.secret,
        provisioning_uri=result.provisioning_uri,
    )


@router.post(
    "/mfa/verify",
    response_model=MessageResponse,
    summary="Verify MFA setup (step 2: confirm code)",
)
async def verify_mfa_setup(
    body: VerifyMFARequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Verify the TOTP code to complete MFA setup."""
    handler = VerifyMFASetupHandler(
        user_repository=UserRepository(session),
        mfa_service=_get_mfa_service(),
    )
    await handler.execute(
        VerifyMFASetupCommand(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            code=body.code,
        )
    )
    return MessageResponse(message="MFA has been enabled successfully")


@router.post(
    "/mfa/disable",
    response_model=MessageResponse,
    summary="Disable MFA",
)
async def disable_mfa(
    body: DisableMFARequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Disable MFA (requires password confirmation)."""
    handler = DisableMFAHandler(
        user_repository=UserRepository(session),
        password_service=_get_password_service(),
    )
    await handler.execute(
        DisableMFACommand(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            password=body.password,
        )
    )
    return MessageResponse(message="MFA has been disabled")
