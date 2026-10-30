"""Add location tracking, SOS requests, and private chat tables.

Revision ID: 002
Revises: 001
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from app.db import Base
import app.models  # noqa: F401

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = ("user_locations", "sos_requests", "chat_messages")


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(
        bind=bind,
        tables=[Base.metadata.tables[name] for name in _TABLES],
    )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(
        bind=bind,
        tables=[Base.metadata.tables[name] for name in reversed(_TABLES)],
    )
