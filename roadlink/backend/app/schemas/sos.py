"""Schemas for SOS requests and emergency assistance."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class SOSCreateRequest(BaseModel):
    category: str = Field(..., max_length=40)
    urgency: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    description: str | None = Field(default=None, max_length=1000)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    initial_radius_m: int = Field(default=5000, ge=1000, le=100000)


class SOSResolveRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class SOSCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SOSOut(BaseModel):
    id: str
    requester_id: str
    requester_name: str
    requester_vehicle: str | None = None
    responder_id: str | None = None
    responder_name: str | None = None
    responder_vehicle: str | None = None
    category: str
    urgency: str
    description: str | None = None
    latitude: float
    longitude: float
    current_radius_m: int
    status: str
    distance_m: int | None = None
    accepted_at: datetime | None = None
    resolved_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    id: str
    sos_id: str
    sender_id: str
    sender_name: str
    content: str
    created_at: datetime

