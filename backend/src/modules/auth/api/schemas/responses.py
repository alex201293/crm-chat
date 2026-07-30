"""Pydantic response schemas for auth endpoints."""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """JWT token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds until access token expires


class UserProfileResponse(BaseModel):
    """User profile data."""

    id: str
    tenant_id: str
    email: str
    full_name: str
    avatar_url: str | None
    phone: str | None
    is_verified: bool
    mfa_enabled: bool
    roles: list[str]
    permissions: list[str]
    tenant_name: str | None
    created_at: str


class AuthResponse(BaseModel):
    """Full authentication response (login/register)."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserProfileResponse
    mfa_required: bool = False


class MFASetupResponse(BaseModel):
    """MFA setup response with provisioning data."""

    secret: str
    provisioning_uri: str
    qr_instructions: str = "Scan this QR code with your authenticator app"


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
