"""Security utilities: password hashing and JWT tokens."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.config import get_settings

_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def create_access_token(user_id: str) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=settings.ACCESS_TOKEN_TTL_S)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token, exp


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token. Raises jwt.InvalidTokenError on failure."""
    settings = get_settings()
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def create_refresh_token_raw() -> str:
    """Return a raw (unhashed) refresh token string."""
    return str(uuid.uuid4()) + str(uuid.uuid4())


def hash_token(token: str) -> str:
    """Hash a refresh token for storage (not password hash — use SHA256 instead for speed)."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()
