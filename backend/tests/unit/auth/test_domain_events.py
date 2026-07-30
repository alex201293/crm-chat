"""Unit tests for domain events and event bus."""

import uuid

import pytest

from src.modules.auth.domain.events.auth_events import (
    MFAEnabled,
    PasswordChanged,
    PasswordResetRequested,
    UserDeactivated,
    UserLoggedIn,
    UserRegistered,
)
from src.shared.domain.events import EventBus


class TestDomainEvents:
    """Tests for auth domain events."""

    def test_user_registered_event(self):
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        event = UserRegistered(user_id=user_id, tenant_id=tenant_id, email="test@example.com")

        assert event.event_type == "UserRegistered"
        assert event.user_id == user_id
        assert event.tenant_id == tenant_id
        assert event.email == "test@example.com"
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_user_logged_in_event(self):
        user_id = uuid.uuid4()
        event = UserLoggedIn(user_id=user_id, ip_address="10.0.0.1")

        assert event.event_type == "UserLoggedIn"
        assert event.user_id == user_id
        assert event.ip_address == "10.0.0.1"

    def test_password_changed_event(self):
        user_id = uuid.uuid4()
        event = PasswordChanged(user_id=user_id)
        assert event.event_type == "PasswordChanged"
        assert event.user_id == user_id

    def test_mfa_enabled_event(self):
        user_id = uuid.uuid4()
        event = MFAEnabled(user_id=user_id)
        assert event.event_type == "MFAEnabled"

    def test_password_reset_requested_event(self):
        user_id = uuid.uuid4()
        event = PasswordResetRequested(user_id=user_id, email="user@test.com")
        assert event.event_type == "PasswordResetRequested"
        assert event.email == "user@test.com"

    def test_user_deactivated_event(self):
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        event = UserDeactivated(user_id=user_id, tenant_id=tenant_id)
        assert event.event_type == "UserDeactivated"

    def test_events_have_unique_ids(self):
        event1 = PasswordChanged(user_id=uuid.uuid4())
        event2 = PasswordChanged(user_id=uuid.uuid4())
        assert event1.event_id != event2.event_id


class TestEventBus:
    """Tests for the in-process event bus."""

    @pytest.mark.asyncio
    async def test_publish_to_subscriber(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(UserRegistered, handler)

        event = UserRegistered(
            user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="t@t.com"
        )
        await bus.publish(event)

        assert len(received) == 1
        assert received[0] == event

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = EventBus()
        results_a = []
        results_b = []

        async def handler_a(event):
            results_a.append(event)

        async def handler_b(event):
            results_b.append(event)

        bus.subscribe(UserRegistered, handler_a)
        bus.subscribe(UserRegistered, handler_b)

        event = UserRegistered(
            user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="t@t.com"
        )
        await bus.publish(event)

        assert len(results_a) == 1
        assert len(results_b) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(UserRegistered, handler)
        bus.unsubscribe(UserRegistered, handler)

        await bus.publish(
            UserRegistered(
                user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="t@t.com"
            )
        )

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_publish_all(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(UserRegistered, handler)
        bus.subscribe(UserLoggedIn, handler)

        events = [
            UserRegistered(
                user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="t@t.com"
            ),
            UserLoggedIn(user_id=uuid.uuid4()),
        ]
        await bus.publish_all(events)

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_no_subscribers_no_error(self):
        bus = EventBus()
        # Should not raise
        await bus.publish(PasswordChanged(user_id=uuid.uuid4()))
