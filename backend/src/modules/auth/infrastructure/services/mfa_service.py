"""MFA (Multi-Factor Authentication) service using TOTP."""

import pyotp


class MFAService:
    """
    Time-based One-Time Password (TOTP) service.
    Compatible with Google Authenticator, Authy, etc.
    """

    def generate_secret(self) -> str:
        """Generate a new TOTP secret for a user."""
        return pyotp.random_base32()

    def get_provisioning_uri(
        self, secret: str, email: str, issuer: str = "CRM Chat"
    ) -> str:
        """
        Generate the OTP Auth URI for QR code display.
        Users scan this with their authenticator app.
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code against the secret.
        Allows a 30-second window tolerance (valid_window=1).
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    def get_current_code(self, secret: str) -> str:
        """Get the current TOTP code (for testing only)."""
        totp = pyotp.TOTP(secret)
        return totp.now()
