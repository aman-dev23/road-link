"""Location models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.db import Base


class UserLocation(Base):
    __tablename__ = "user_locations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90.0 AND 90.0", name="ck_location_latitude"),
        CheckConstraint("longitude BETWEEN -180.0 AND 180.0", name="ck_location_longitude"),
    )

    user = relationship("User", backref="location", lazy="joined")

