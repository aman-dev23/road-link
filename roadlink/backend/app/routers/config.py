"""Config router - exposes app configuration to the frontend."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["config"])

CATEGORIES = [
    "VEHICLE_BREAKDOWN", "FUEL_SHORTAGE", "MEDICAL_EMERGENCY", "ACCIDENT",
    "FOOD_WATER", "MECHANICAL_ASSISTANCE", "NEED_DIRECTIONS", "OTHER",
]
URGENCIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ASSISTANCE_TYPES = [
    "MECHANIC", "FIRST_AID", "TOWING", "FUEL", "WATER_FOOD",
    "DIRECTIONS", "TRANSPORT", "OTHER",
]
VEHICLE_TYPES = ["CAR", "BIKE", "TRUCK", "SOLO_WALKER", "GROUP", "MECHANIC", "OTHER"]
SKILLS = ["MECHANIC", "FIRST_AID", "TOWING", "FUEL_SUPPLY", "NAVIGATION_HELP", "TRANSLATION", "OTHER"]


@router.get("/config")
async def get_config():
    settings = get_settings()
    return {
        "radius_options_m": settings.radius_options_list,
        "sos_stages_m": settings.sos_stages_list,
        "sos_stage_delays_s": settings.sos_delays_list,
        "emergency_number": settings.EMERGENCY_NUMBER,
        "limits": {
            "max_description": 1000,
            "max_message": 2000,
            "max_image_bytes": settings.MAX_IMAGE_BYTES,
        },
        "categories": CATEGORIES,
        "urgencies": URGENCIES,
        "assistance_types": ASSISTANCE_TYPES,
        "vehicle_types": VEHICLE_TYPES,
        "skills": SKILLS,
        "ai_enabled": settings.AI_PROVIDER == "ollama",
    }
