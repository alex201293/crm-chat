"""Pydantic request schemas for auth endpoints."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration request payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Login request payload."""

    email: EmailStr
    password: str = Field(min_length=1)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=6)


class RefreshTokenRequest(BaseModel):
    """Token refresh request payload."""

    refresh_token: str = Field(min_length=1)


class RequestResetPasswordRequest(BaseModel):
    """Password reset request payload."""

    email: EmailStr


class ConfirmResetPasswordRequest(BaseModel):
    """Password reset confirmation payload."""

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyMFARequest(BaseModel):
    """MFA code verification payload."""

    code: str = Field(min_length=6, max_length=6)


class DisableMFARequest(BaseModel):
    """MFA disable payload (requires password confirmation)."""

    password: str = Field(min_length=1)
