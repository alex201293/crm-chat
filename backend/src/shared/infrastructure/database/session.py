"""
Async database session management.
Provides session factory and dependency injection for FastAPI.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import get_settings

settings = get_settings()

# Async engine with connection pooling
engine = create_async_engine(
    settings.database.async_database_url,
    pool_size=settings.database.DATABASE_POOL_SIZE,
    max_overflow=settings.database.DATABASE_MAX_OVERFLOW,
    echo=settings.database.DATABASE_ECHO,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    Automatically commits on success and rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
