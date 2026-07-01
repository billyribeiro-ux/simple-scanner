from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


def get_engine():
    settings = get_settings()
    url = settings.database_url or "postgresql+asyncpg://amd:amd@localhost:5432/adaptive_market_decoder"
    return create_async_engine(url, future=True)


async def get_session() -> AsyncIterator[AsyncSession]:
    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
