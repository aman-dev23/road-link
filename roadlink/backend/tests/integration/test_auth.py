"""Integration tests for auth endpoints."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword123",
        "display_name": "Test User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@example.com",
        "password": "securepassword123",
        "display_name": "Dup User",
    }
    await client.post("/api/auth/register", json=payload)
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "short@example.com",
        "password": "short",
        "display_name": "Short Pass",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "securepassword123",
        "display_name": "Login User",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "securepassword123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "wrongpw@example.com",
        "password": "securepassword123",
        "display_name": "Wrong PW",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "wrongpassword123",
    })
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "somepassword123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "refresh@example.com",
        "password": "securepassword123",
        "display_name": "Refresh User",
    })
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_refresh = resp.json()["refresh_token"]
    assert new_refresh != refresh_token


@pytest.mark.asyncio
async def test_refresh_reuse_detection(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "reuse@example.com",
        "password": "securepassword123",
        "display_name": "Reuse User",
    })
    original_refresh = reg.json()["refresh_token"]

    # First use (succeeds, rotates)
    await client.post("/api/auth/refresh", json={"refresh_token": original_refresh})

    # Second use of original (reuse detection)
    resp = await client.post("/api/auth/refresh", json={"refresh_token": original_refresh})
    assert resp.status_code == 401
    assert "reuse" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "logout@example.com",
        "password": "securepassword123",
        "display_name": "Logout User",
    })
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 204

    # After logout, refresh should fail
    resp2 = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    resp = await client.get("/api/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_token(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "getme@example.com",
        "password": "securepassword123",
        "display_name": "Get Me User",
    })
    token = reg.json()["access_token"]
    resp = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "getme@example.com"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_config_endpoint(client: AsyncClient):
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "radius_options_m" in data
    assert "categories" in data
    assert "emergency_number" in data
