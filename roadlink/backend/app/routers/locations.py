"""Location router: update location, fetch nearby travellers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import CurrentUser, DB
from app.models.locations import UserLocation
from app.models.users import User, UserProfile, UserSkill
from app.schemas.locations import (
    LocationUpdateRequest,
    LocationUpdateResponse,
    NearbyTraveller,
)
from app.services.geo import bounding_box, haversine_distance_m

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.post("/update", response_model=LocationUpdateResponse)
async def update_location(
    body: LocationUpdateRequest,
    current_user: CurrentUser,
    db: DB,
):
    """Upsert caller's current location coordinates."""
    result = await db.execute(
        select(UserLocation).where(UserLocation.user_id == current_user.id)
    )
    loc = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if loc is None:
        loc = UserLocation(
            user_id=current_user.id,
            latitude=body.latitude,
            longitude=body.longitude,
            accuracy_m=body.accuracy_m,
            speed_mps=body.speed_mps,
            heading_deg=body.heading_deg,
            updated_at=now,
        )
        db.add(loc)
    else:
        loc.latitude = body.latitude
        loc.longitude = body.longitude
        loc.accuracy_m = body.accuracy_m
        loc.speed_mps = body.speed_mps
        loc.heading_deg = body.heading_deg
        loc.updated_at = now

    await db.commit()
    await db.refresh(loc)

    return LocationUpdateResponse(
        status="ok",
        latitude=loc.latitude,
        longitude=loc.longitude,
        updated_at=loc.updated_at,
    )


@router.get("/me")
async def get_my_location(current_user: CurrentUser, db: DB):
    """Get caller's last known location."""
    result = await db.execute(
        select(UserLocation).where(UserLocation.user_id == current_user.id)
    )
    loc = result.scalar_one_or_none()
    if not loc:
        return {"has_location": False, "location": None}

    return {
        "has_location": True,
        "location": {
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "accuracy_m": loc.accuracy_m,
            "speed_mps": loc.speed_mps,
            "heading_deg": loc.heading_deg,
            "updated_at": loc.updated_at.isoformat(),
        },
    }


@router.get("/nearby", response_model=list[NearbyTraveller])
async def get_nearby_travellers(
    current_user: CurrentUser,
    db: DB,
    radius_m: int = Query(default=25000, ge=100, le=200000),
    latitude: float | None = Query(default=None, ge=-90.0, le=90.0),
    longitude: float | None = Query(default=None, ge=-180.0, le=180.0),
):
    """Find nearby active travellers within the given radius in meters."""
    ref_lat = latitude
    ref_lon = longitude

    # If not provided, fetch caller's location
    if ref_lat is None or ref_lon is None:
        my_loc_res = await db.execute(
            select(UserLocation).where(UserLocation.user_id == current_user.id)
        )
        my_loc = my_loc_res.scalar_one_or_none()
        if not my_loc:
            return []
        ref_lat = my_loc.latitude
        ref_lon = my_loc.longitude

    # Compute bounding box for pre-filtering
    min_lat, max_lat, min_lon, max_lon = bounding_box(ref_lat, ref_lon, radius_m)
    active_since = datetime.now(timezone.utc) - timedelta(
        seconds=get_settings().ACTIVE_WINDOW_S
    )

    stmt = (
        select(UserLocation, UserProfile)
        .join(User, User.id == UserLocation.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .where(
            UserLocation.user_id != current_user.id,
            User.status == "ACTIVE",
            UserProfile.visibility == "VISIBLE",
            UserLocation.latitude >= min_lat,
            UserLocation.latitude <= max_lat,
            UserLocation.longitude >= min_lon,
            UserLocation.longitude <= max_lon,
            UserLocation.updated_at >= active_since,
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Pre-fetch skills for matched users
    user_ids = [loc.user_id for loc, _ in rows]
    skills_map: dict[str, list[str]] = {}
    if user_ids:
        skills_stmt = select(UserSkill).where(UserSkill.user_id.in_(user_ids))
        skills_res = await db.execute(skills_stmt)
        for s in skills_res.scalars().all():
            skills_map.setdefault(str(s.user_id), []).append(s.skill)

    travellers: list[NearbyTraveller] = []
    for loc, profile in rows:
        dist_m = int(haversine_distance_m(ref_lat, ref_lon, loc.latitude, loc.longitude))
        if dist_m <= radius_m:
            uid_str = str(loc.user_id)
            dname = profile.display_name if profile else "Traveller"
            vtype = profile.vehicle_type if profile else "OTHER"
            vdesc = profile.vehicle_description if profile else None
            is_avail = profile.is_available if profile else True
            travellers.append(
                NearbyTraveller(
                    user_id=uid_str,
                    display_name=dname,
                    avatar_url=f"/api/media/{profile.avatar_key}" if (profile and profile.avatar_key) else None,
                    vehicle_type=vtype,
                    vehicle_description=vdesc,
                    skills=skills_map.get(uid_str, []),
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    distance_m=dist_m,
                    is_available=is_avail,
                    updated_at=loc.updated_at,
                )
            )

    travellers.sort(key=lambda t: t.distance_m)
    return travellers
