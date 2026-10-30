"""Pydantic schemas for /api/me endpoints."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


VEHICLE_TYPES = Literal["CAR", "BIKE", "TRUCK", "SOLO_WALKER", "GROUP", "MECHANIC", "OTHER"]
SKILL_TYPES = Literal[
    "MECHANIC", "FIRST_AID", "TOWING", "FUEL_SUPPLY", "NAVIGATION_HELP", "TRANSLATION", "OTHER"
]
VISIBILITY_TYPES = Literal["VISIBLE", "HIDDEN"]
RADIUS_OPTIONS = Literal[5000, 10000, 25000, 50000, 100000]


class ProfileOut(BaseModel):
    user_id: str
    display_name: str
    avatar_key: str | None
    avatar_url: str | None = None
    vehicle_type: str
    vehicle_description: str | None
    preferred_language: str
    is_available: bool
    visibility: str
    receive_sos: bool
    default_radius_m: int
    onboarding_completed: bool

    model_config = {"from_attributes": True}


class UserWithProfile(BaseModel):
    id: str
    email: str
    status: str
    sos_restricted: bool
    profile: ProfileOut | None
    skills: list[str]


class PatchProfileRequest(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=40)
    vehicle_type: VEHICLE_TYPES | None = None
    vehicle_description: str | None = Field(None, max_length=100)
    preferred_language: str | None = Field(None, max_length=10)
    is_available: bool | None = None
    visibility: VISIBILITY_TYPES | None = None
    receive_sos: bool | None = None
    default_radius_m: RADIUS_OPTIONS | None = None
    onboarding_completed: bool | None = None


class PutSkillsRequest(BaseModel):
    skills: list[SKILL_TYPES] = Field(max_length=7)


class DeleteAccountRequest(BaseModel):
    password: str
