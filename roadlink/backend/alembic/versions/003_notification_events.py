"""Persist notification events for cross-worker reconnect replay.

Revision ID: 003
Revises: 002
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from app.db import Base
import app.models  # noqa: F401

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(
        bind=bind,
        tables=[Base.metadata.tables["notification_events"]],
    )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(
        bind=bind,
        tables=[Base.metadata.tables["notification_events"]],
    )
