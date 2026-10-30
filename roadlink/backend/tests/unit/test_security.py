"""Unit tests for security utilities."""
from __future__ import annotations

import time
import jwt
import pytest

from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token_raw,
    hash_token,
)
from app.config import get_settings


def test_password_hash_and_verify():
    password = "securepassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_wrong_password_rejected():
    hashed = hash_password("correctpassword")
    assert not verify_password("wrongpassword", hashed)


def test_access_token_round_trip():
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    token, exp = create_access_token(user_id)
    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


def test_access_token_wrong_secret():
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    token, _ = create_access_token(user_id)
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(token, "wrong_secret", algorithms=["HS256"])


def test_refresh_token_is_unique():
    t1 = create_refresh_token_raw()
    t2 = create_refresh_token_raw()
    assert t1 != t2


def test_hash_token_deterministic():
    raw = "some-token-string"
    h1 = hash_token(raw)
    h2 = hash_token(raw)
    assert h1 == h2
    assert h1 != raw
