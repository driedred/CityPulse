from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models import IssueCategory
from app.scripts.seed import seed_categories_in_session


@pytest_asyncio.fixture
async def session_factory(
    tmp_path: Path,
) -> async_sessionmaker[AsyncSession]:
    database_path = tmp_path / "citypulse-test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}",
        future=True,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        await seed_categories_in_session(session)
        await session.commit()

    yield factory

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_category_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    async with session_factory() as session:
        category = await session.scalar(
            select(IssueCategory).where(IssueCategory.slug == "roads")
        )
        assert category is not None
        return str(category.id)
