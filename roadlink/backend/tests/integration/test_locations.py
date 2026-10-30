"""Integration tests for location tracking and nearby discovery."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.locations import UserLocation


async def _register(client: AsyncClient, email: str, name: str) -> str:
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": name,
    })
    assert resp.status_code == 201
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_update_location(client: AsyncClient):
    token = await _register(client, "loc1@example.com", "Loc User")
    resp = await client.post(
        "/api/locations/update",
        json={"latitude": 28.6139, "longitude": 77.2090, "accuracy_m": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["latitude"] == 28.6139
    assert data["longitude"] == 77.2090

    # Verify get_my_location
    me_resp = await client.get("/api/locations/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["has_location"] is True


@pytest.mark.asyncio
async def test_nearby_traveller_discovery(client: AsyncClient):
    # Register User A in Delhi (Connaught Place: 28.6315, 77.2167)
    token_a = await _register(client, "alice@example.com", "Alice Delhi")
    await client.post(
        "/api/locations/update",
        json={"latitude": 28.6315, "longitude": 77.2167},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Register User B in nearby Karol Bagh (~3 km away: 28.6517, 77.1906)
    token_b = await _register(client, "bob@example.com", "Bob Karol Bagh")
    await client.post(
        "/api/locations/update",
        json={"latitude": 28.6517, "longitude": 77.1906},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    # Register User C far away in Mumbai (18.9220, 72.8347: ~1150 km away)
    token_c = await _register(client, "charlie@example.com", "Charlie Mumbai")
    await client.post(
        "/api/locations/update",
        json={"latitude": 18.9220, "longitude": 72.8347},
        headers={"Authorization": f"Bearer {token_c}"},
    )

    # Alice queries nearby travellers within 10 km (10,000 m)
    resp = await client.get(
        "/api/locations/nearby?radius_m=10000",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    nearby = resp.json()

    # Bob should be found within 10km, Charlie should NOT be found
    names = [t["display_name"] for t in nearby]
    assert "Bob Karol Bagh" in names
    assert "Charlie Mumbai" not in names
    assert "Alice Delhi" not in names  # Should not include self

    # Check distance calculation
    bob_info = next(t for t in nearby if t["display_name"] == "Bob Karol Bagh")
    assert 2000 < bob_info["distance_m"] < 5000


@pytest.mark.asyncio
async def test_nearby_excludes_stale_locations(client: AsyncClient, db):
    token_a = await _register(client, "fresh-user@example.com", "Fresh User")
    token_b = await _register(client, "stale-user@example.com", "Stale User")
    await client.post(
        "/api/locations/update",
        json={"latitude": 28.6139, "longitude": 77.2090},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    await client.post(
        "/api/locations/update",
        json={"latitude": 28.6140, "longitude": 77.2090},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    user = await client.get(
        "/api/me", headers={"Authorization": f"Bearer {token_b}"}
    )
    await db.execute(
        update(UserLocation)
        .where(UserLocation.user_id == uuid.UUID(user.json()["id"]))
        .values(updated_at=datetime.now(timezone.utc) - timedelta(minutes=10))
    )
    await db.commit()

    response = await client.get(
        "/api/locations/nearby?radius_m=10000",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    assert "Stale User" not in [traveller["display_name"] for traveller in response.json()]
