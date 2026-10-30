"""Auth service: registration, login, token management."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.users import RefreshToken, User, UserProfile
from app.security import (
    create_access_token,
    create_refresh_token_raw,
    hash_password,
    hash_token,
    verify_password,
)


class AuthError(Exception):
    """Raised for known auth failures (e.g. bad credentials, reuse detected)."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    display_name: str,
) -> tuple[User, str, str]:
    """
    Create a new user and profile.
    Returns (user, access_token, raw_refresh_token).
    Raises AuthError if the email is already taken.
    """
    # Check for duplicate email (citext handles case insensitivity in DB)
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise AuthError("EMAIL_TAKEN", "An account with this email already exists")

    user = User(
        id=uuid.uuid4(),
        email=email.lower(),
        password_hash=hash_password(password),
        status="ACTIVE",
    )
    db.add(user)
    await db.flush()

    profile = UserProfile(
        user_id=user.id,
        display_name=display_name,
    )
    db.add(profile)
    await db.flush()

    access_token, _ = create_access_token(str(user.id))
    raw_refresh, _ = await _create_refresh_token(db, user.id)
    await db.commit()
    return user, access_token, raw_refresh


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, str, str]:
    """
    Authenticate a user.
    Returns (user, access_token, raw_refresh_token).
    Raises AuthError for invalid credentials (generic message to avoid enumeration).
    """
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()

    # Always run the hash check (even if user doesn't exist) to prevent timing attacks
    dummy_hash = "$argon2id$v=19$m=65536,t=2,p=2$dummydummydummy$dummydummydummy"
    password_ok = verify_password(password, user.password_hash if user else dummy_hash)

    if not user or not password_ok or user.status != "ACTIVE":
        raise AuthError("INVALID_CREDENTIALS", "Invalid email or password")

    access_token, _ = create_access_token(str(user.id))
    raw_refresh, _ = await _create_refresh_token(db, user.id)
    await db.commit()
    return user, access_token, raw_refresh


async def rotate_refresh_token(
    db: AsyncSession,
    raw_token: str,
) -> tuple[User, str, str]:
    """
    Rotate a refresh token (issue new pair).
    Raises AuthError on invalid/revoked/expired tokens.
    Revokes the entire family if token reuse is detected.
    """
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if not stored:
        raise AuthError("INVALID_REFRESH", "Refresh token not found")

    now = datetime.now(timezone.utc)

    if stored.revoked_at is not None:
        # Token reuse detected — revoke the entire family
        await _revoke_family(db, stored.family_id)
        await db.commit()
        raise AuthError("INVALID_REFRESH", "Refresh token reuse detected; please log in again")

    if stored.expires_at.replace(tzinfo=timezone.utc) < now:
        raise AuthError("INVALID_REFRESH", "Refresh token has expired")

    # Revoke the current token
    stored.revoked_at = now

    # Get the user
    user_result = await db.execute(
        select(User).where(User.id == stored.user_id, User.status == "ACTIVE")
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise AuthError("INVALID_REFRESH", "User not found or inactive")

    # Issue new tokens in the same family
    access_token, _ = create_access_token(str(user.id))
    raw_refresh, new_rt = await _create_refresh_token(db, user.id, stored.family_id)
    stored.replaced_by = new_rt.id
    await db.commit()
    return user, access_token, raw_refresh


async def logout_user(db: AsyncSession, raw_token: str) -> None:
    """Revoke the token's entire family."""
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if stored:
        await _revoke_family(db, stored.family_id)
        await db.commit()


async def _create_refresh_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    family_id: uuid.UUID | None = None,
) -> tuple[str, RefreshToken]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    raw = create_refresh_token_raw()
    rt = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=family_id or uuid.uuid4(),
        token_hash=hash_token(raw),
        expires_at=now + timedelta(seconds=settings.REFRESH_TOKEN_TTL_S),
    )
    db.add(rt)
    await db.flush()
    return raw, rt


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
