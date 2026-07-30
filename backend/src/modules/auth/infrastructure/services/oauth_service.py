"""OAuth provider integrations for Google and Microsoft."""

from dataclasses import dataclass

import httpx

from src.config.settings import get_settings


@dataclass
class OAuthUserInfo:
    """Normalized user information from OAuth providers."""

    provider: str  # "google" | "microsoft"
    provider_id: str
    email: str
    full_name: str
    avatar_url: str | None


class GoogleOAuthService:
    """Google OAuth2 integration."""

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self) -> None:
        settings = get_settings()
        self._client_id = settings.app.APP_SECRET_KEY  # Placeholder: use dedicated settings
        self._client_secret = ""
        self._redirect_uri = ""

    def get_authorization_url(self, state: str) -> str:
        """Generate the Google OAuth authorization URL."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    async def exchange_code(self, code: str) -> OAuthUserInfo:
        """Exchange authorization code for user info."""
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self._redirect_uri,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            # Get user info
            userinfo_response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            userinfo_response.raise_for_status()
            user_data = userinfo_response.json()

        return OAuthUserInfo(
            provider="google",
            provider_id=user_data["id"],
            email=user_data["email"],
            full_name=user_data.get("name", ""),
            avatar_url=user_data.get("picture"),
        )


class MicrosoftOAuthService:
    """Microsoft OAuth2 integration (Azure AD)."""

    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

    def __init__(self) -> None:
        settings = get_settings()
        self._client_id = ""
        self._client_secret = ""
        self._redirect_uri = ""

    def get_authorization_url(self, state: str) -> str:
        """Generate the Microsoft OAuth authorization URL."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "response_mode": "query",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{query}"

    async def exchange_code(self, code: str) -> OAuthUserInfo:
        """Exchange authorization code for user info."""
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self._redirect_uri,
                    "scope": "openid email profile User.Read",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            # Get user info from Microsoft Graph
            userinfo_response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            userinfo_response.raise_for_status()
            user_data = userinfo_response.json()

        return OAuthUserInfo(
            provider="microsoft",
            provider_id=user_data["id"],
            email=user_data.get("mail") or user_data.get("userPrincipalName", ""),
            full_name=user_data.get("displayName", ""),
            avatar_url=None,  # Microsoft Graph requires separate call for photo
        )
