"""Test configuration and fixtures."""
from __future__ import annotations

import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings
from app.db import Base, get_db
from app.main import create_app


@pytest_asyncio.fixture
async def test_engine():
    test_db_file = "test_roadlink.db"
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass
    db_url = f"sqlite+aiosqlite:///{test_db_file}"
    engine = create_async_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass


@pytest_asyncio.fixture
async def db(test_engine):
    """Provide a test database session."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    """Test HTTP client with DB override."""
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
