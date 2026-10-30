"""Async database engine and session factory."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str | None = None):
    settings = get_settings()
    db_url = url or settings.DATABASE_URL
    kwargs = {"echo": settings.ENV == "development"}
    if "sqlite" in db_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update({
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
        })
    return create_async_engine(db_url, **kwargs)


_engine = None
_session_factory = None


def get_engine(url: str | None = None):
    global _engine
    if _engine is None:
        _engine = _make_engine(url)
    return _engine


def get_session_factory(url: str | None = None) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(url), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db(url: str | None = None) -> None:
    """Initialize engine (called from lifespan)."""
    get_engine(url)
    get_session_factory(url)
