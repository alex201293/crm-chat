"""
Shared test fixtures for the backend test suite.
Provides test client, database session, and factory helpers.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import get_settings
from src.main import app
from src.shared.infrastructure.database.base import Base
from src.shared.infrastructure.database.session import get_db_session

# Use SQLite for unit tests (no external dependencies)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def override_db_session(db_session: AsyncSession):
    """Override the app's DB session dependency with test session."""

    async def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_db_session) -> TestClient:
    """Provide a synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(override_db_session) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
