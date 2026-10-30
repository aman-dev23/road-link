"""SQLAlchemy models: users, profiles, refresh_tokens."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )
    sos_restricted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE','SUSPENDED','DELETED')",
            name="ck_users_status",
        ),
    )

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False, lazy="joined"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", lazy="select"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(40), nullable=False)
    avatar_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OTHER", server_default="OTHER"
    )
    vehicle_description: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en", server_default="en"
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    visibility: Mapped[str] = mapped_column(
        String(10), nullable=False, default="VISIBLE", server_default="VISIBLE"
    )
    receive_sos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    default_radius_m: Mapped[int] = mapped_column(
        nullable=False, default=25000, server_default="25000"
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "length(display_name) BETWEEN 2 AND 40",
            name="ck_profile_display_name_len",
        ),
        CheckConstraint(
            "vehicle_type IN ('CAR','BIKE','TRUCK','SOLO_WALKER','GROUP','MECHANIC','OTHER')",
            name="ck_profile_vehicle_type",
        ),
        CheckConstraint(
            "visibility IN ('VISIBLE','HIDDEN')",
            name="ck_profile_visibility",
        ),
        CheckConstraint(
            "default_radius_m IN (5000,10000,25000,50000,100000)",
            name="ck_profile_default_radius",
        ),
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")
    skills: Mapped[list["UserSkill"]] = relationship(
        "UserSkill", back_populates="user_profile", lazy="select",
        primaryjoin="UserProfile.user_id == UserSkill.user_id",
        foreign_keys="UserSkill.user_id",
    )


class UserSkill(Base):
    __tablename__ = "user_skills"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill: Mapped[str] = mapped_column(String(30), primary_key=True)

    __table_args__ = (
        CheckConstraint(
            "skill IN ('MECHANIC','FIRST_AID','TOWING','FUEL_SUPPLY',"
            "'NAVIGATION_HELP','TRANSLATION','OTHER')",
            name="ck_skill_value",
        ),
    )

    user_profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="skills",
        primaryjoin="UserSkill.user_id == UserProfile.user_id",
        foreign_keys=[user_id],
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True, default=uuid.uuid4
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
