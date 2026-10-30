"""001 initial schema: extensions, users, profiles, skills, refresh_tokens.

Revision ID: 001
Revises:
Create Date: 2026-10-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        from app.db import Base
        import app.models  # noqa: F401

        Base.metadata.create_all(
            bind=op.get_bind(),
            tables=[
                Base.metadata.tables[name]
                for name in ("users", "user_profiles", "user_skills", "refresh_tokens")
            ],
        )
        return

    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("sos_restricted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('ACTIVE','SUSPENDED','DELETED')", name="ck_users_status"),
    )
    op.execute("ALTER TABLE users ALTER COLUMN email TYPE citext")
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # user_profiles
    op.create_table(
        "user_profiles",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("display_name", sa.String(40), nullable=False),
        sa.Column("avatar_key", sa.Text(), nullable=True),
        sa.Column("vehicle_type", sa.String(20), nullable=False, server_default="OTHER"),
        sa.Column("vehicle_description", sa.String(100), nullable=True),
        sa.Column("preferred_language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="VISIBLE"),
        sa.Column("receive_sos", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("default_radius_m", sa.Integer(), nullable=False, server_default="25000"),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("char_length(display_name) BETWEEN 2 AND 40", name="ck_profile_display_name_len"),
        sa.CheckConstraint(
            "vehicle_type IN ('CAR','BIKE','TRUCK','SOLO_WALKER','GROUP','MECHANIC','OTHER')",
            name="ck_profile_vehicle_type",
        ),
        sa.CheckConstraint("visibility IN ('VISIBLE','HIDDEN')", name="ck_profile_visibility"),
        sa.CheckConstraint(
            "default_radius_m IN (5000,10000,25000,50000,100000)",
            name="ck_profile_default_radius",
        ),
    )

    # user_skills
    op.create_table(
        "user_skills",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill", sa.String(30), primary_key=True),
        sa.CheckConstraint(
            "skill IN ('MECHANIC','FIRST_AID','TOWING','FUEL_SUPPLY','NAVIGATION_HELP','TRANSLATION','OTHER')",
            name="ck_skill_value",
        ),
    )

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        from app.db import Base
        import app.models  # noqa: F401

        Base.metadata.drop_all(
            bind=op.get_bind(),
            tables=[
                Base.metadata.tables[name]
                for name in ("users", "user_profiles", "user_skills", "refresh_tokens")
            ],
        )
        return

    op.drop_table("refresh_tokens")
    op.drop_table("user_skills")
    op.drop_table("user_profiles")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS postgis")
    op.execute("DROP EXTENSION IF EXISTS citext")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
