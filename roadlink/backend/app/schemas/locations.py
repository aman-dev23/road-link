"""Schemas for location updates and nearby travellers."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class LocationUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy_m: float | None = Field(default=None, ge=0.0)
    speed_mps: float | None = Field(default=None, ge=0.0)
    heading_deg: float | None = Field(default=None, ge=0.0, le=360.0)


class LocationUpdateResponse(BaseModel):
    status: str = "ok"
    latitude: float
    longitude: float
    updated_at: datetime


class NearbyTraveller(BaseModel):
    user_id: str
    display_name: str
    avatar_url: str | None = None
    vehicle_type: str
    vehicle_description: str | None = None
    skills: list[str] = []
    latitude: float
    longitude: float
    distance_m: int
    is_available: bool
    updated_at: datetime

