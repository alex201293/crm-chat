"""Unit tests for auth domain entities."""

import uuid

import pytest

from src.modules.auth.domain.entities.tenant import Tenant
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.password import HashedPassword


class TestUser:
    """Tests for User aggregate root."""

    def _make_user(self, **kwargs) -> User:
        defaults = {
            "tenant_id": uuid.uuid4(),
            "email": Email("test@example.com"),
            "password_hash": HashedPassword(
                "$2b$12$LJ3m4lKx0z3q5v6w7x8y9OuRsT1u2V3w4X5y6Z7a8B9c0D1e2F3g"
            ),
            "full_name": "Test User",
            "roles": ["agent"],
            "permissions": {"conversations:read", "contacts:read"},
        }
        defaults.update(kwargs)
        return User(**defaults)

    def test_create_factory(self):
        tenant_id = uuid.uuid4()
        email = Email("new@example.com")
        password_hash = HashedPassword(
            "$2b$12$LJ3m4lKx0z3q5v6w7x8y9OuRsT1u2V3w4X5y6Z7a8B9c0D1e2F3g"
        )

        user = User.create(
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
            full_name="New User",
        )

        assert user.id is not None
        assert user.tenant_id == tenant_id
        assert user.email == email
        assert user.full_name == "New User"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.mfa_enabled is False

    def test_create_emits_user_registered_event(self):
        user = User.create(
            tenant_id=uuid.uuid4(),
            email=Email("test@example.com"),
            password_hash=HashedPassword(
                "$2b$12$LJ3m4lKx0z3q5v6w7x8y9OuRsT1u2V3w4X5y6Z7a8B9c0D1e2F3g"
            ),
            full_name="Test",
        )

        events = user.domain_events
        assert len(events) == 1
        assert events[0].event_type == "UserRegistered"

    def test_record_login(self):
        user = self._make_user()
        user.record_login(ip_address="192.168.1.1")

        assert user.last_login_at is not None
        assert user.last_login_ip == "192.168.1.1"
        assert len(user.domain_events) == 1
        assert user.domain_events[0].event_type == "UserLoggedIn"

    def test_change_password(self):
        user = self._make_user()
        new_hash = HashedPassword(
            "$2b$12$AAAA4lKx0z3q5v6w7x8y9OuRsT1u2V3w4X5y6Z7a8B9c0D1e2F3g"
        )
        user.change_password(new_hash)

        assert user.password_hash == new_hash
        assert user.updated_at is not None
        assert len(user.domain_events) == 1
        assert user.domain_events[0].event_type == "PasswordChanged"

    def test_enable_mfa(self):
        user = self._make_user()
        user.enable_mfa("JBSWY3DPEHPK3PXP")

        assert user.mfa_enabled is True
        assert user.mfa_secret == "JBSWY3DPEHPK3PXP"
        assert len(user.domain_events) == 1
        assert user.domain_events[0].event_type == "MFAEnabled"

    def test_disable_mfa(self):
        user = self._make_user(mfa_enabled=True, mfa_secret="SECRET")
        user.disable_mfa()

        assert user.mfa_enabled is False
        assert user.mfa_secret is None

    def test_deactivate(self):
        user = self._make_user()
        user.deactivate()
        assert user.is_active is False

    def test_verify_email(self):
        user = self._make_user(is_verified=False)
        user.verify_email()
        assert user.is_verified is True

    def test_has_permission(self):
        user = self._make_user(permissions={"conversations:read", "contacts:write"})
        assert user.has_permission("conversations:read") is True
        assert user.has_permission("deals:delete") is False

    def test_has_any_permission(self):
        user = self._make_user(permissions={"conversations:read"})
        assert user.has_any_permission(["conversations:read", "deals:write"]) is True
        assert user.has_any_permission(["deals:write", "deals:delete"]) is False

    def test_has_role(self):
        user = self._make_user(roles=["admin", "agent"])
        assert user.has_role("admin") is True
        assert user.has_role("owner") is False

    def test_clear_domain_events(self):
        user = self._make_user()
        user.record_login()
        events = user.clear_domain_events()
        assert len(events) == 1
        assert len(user.domain_events) == 0

    def test_entity_equality_by_id(self):
        user_id = uuid.uuid4()
        user1 = self._make_user()
        user1.id = user_id
        user2 = self._make_user()
        user2.id = user_id
        assert user1 == user2

    def test_entity_inequality(self):
        user1 = self._make_user()
        user2 = self._make_user()
        assert user1 != user2


class TestTenant:
    """Tests for Tenant aggregate root."""

    def test_create_factory(self):
        tenant = Tenant.create(name="Acme Corp", slug="acme-corp")

        assert tenant.id is not None
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.plan == "free"
        assert tenant.is_active is True
        assert tenant.max_users == 5
        assert "ai_provider" in tenant.settings
        assert tenant.settings["language"] == "es"

    def test_can_add_user_within_limit(self):
        tenant = Tenant.create(name="Test", slug="test")
        assert tenant.can_add_user(current_user_count=4) is True

    def test_cannot_add_user_at_limit(self):
        tenant = Tenant.create(name="Test", slug="test")
        assert tenant.can_add_user(current_user_count=5) is False

    def test_upgrade_plan(self):
        tenant = Tenant.create(name="Test", slug="test")
        tenant.upgrade_plan(plan="pro", max_users=50, max_conversations=50000)

        assert tenant.plan == "pro"
        assert tenant.max_users == 50
        assert tenant.max_conversations_per_month == 50000
        assert tenant.updated_at is not None

    def test_deactivate(self):
        tenant = Tenant.create(name="Test", slug="test")
        tenant.deactivate()
        assert tenant.is_active is False
