"""Me/profile router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DB
from app.models.users import User, UserProfile, UserSkill, RefreshToken
from app.schemas.me import (
    DeleteAccountRequest,
    PatchProfileRequest,
    ProfileOut,
    PutSkillsRequest,
    UserWithProfile,
)
from app.security import verify_password

router = APIRouter(prefix="/api/me", tags=["me"])


def _profile_to_out(profile: UserProfile, skills: list[str]) -> ProfileOut:
    return ProfileOut(
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        avatar_key=profile.avatar_key,
        avatar_url=f"/api/media/{profile.avatar_key}" if profile.avatar_key else None,
        vehicle_type=profile.vehicle_type,
        vehicle_description=profile.vehicle_description,
        preferred_language=profile.preferred_language,
        is_available=profile.is_available,
        visibility=profile.visibility,
        receive_sos=profile.receive_sos,
        default_radius_m=profile.default_radius_m,
        onboarding_completed=profile.onboarding_completed,
    )


@router.get("", response_model=UserWithProfile)
async def get_me(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    skills_result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == current_user.id)
    )
    skills = [s.skill for s in skills_result.scalars().all()]

    profile_out = _profile_to_out(profile, skills) if profile else None
    return UserWithProfile(
        id=str(current_user.id),
        email=current_user.email,
        status=current_user.status,
        sos_restricted=current_user.sos_restricted,
        profile=profile_out,
        skills=skills,
    )


@router.patch("/profile", response_model=ProfileOut)
async def patch_profile(body: PatchProfileRequest, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=current_user.id, display_name="User")
        db.add(profile)

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    skills_result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == current_user.id)
    )
    skills = [s.skill for s in skills_result.scalars().all()]
    return _profile_to_out(profile, skills)


@router.put("/skills", response_model=list[str])
async def put_skills(body: PutSkillsRequest, current_user: CurrentUser, db: DB):
    # Replace all skills
    await db.execute(
        delete(UserSkill).where(UserSkill.user_id == current_user.id)
    )
    unique_skills = list(dict.fromkeys(body.skills))  # dedupe preserving order
    for skill in unique_skills:
        db.add(UserSkill(user_id=current_user.id, skill=skill))
    await db.commit()
    return unique_skills


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(body: DeleteAccountRequest, current_user: CurrentUser, db: DB):
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Incorrect password"},
        )
    # Anonymise: mark deleted, clear email
    current_user.status = "DELETED"
    current_user.email = f"deleted_{current_user.id}@roadlink.invalid"
    current_user.password_hash = "DELETED"

    # Revoke all refresh tokens
    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == current_user.id)
    )
    await db.commit()
