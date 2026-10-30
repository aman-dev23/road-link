"""Integration tests for the Core SOS lifecycle, atomic acceptance, and private chat."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.locations import UserLocation
from app.ws.manager import ws_manager


async def _register(client: AsyncClient, email: str, name: str) -> str:
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": name,
    })
    assert resp.status_code == 201
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_full_sos_lifecycle(client: AsyncClient):
    # 1. User A (Requester) registers and updates location
    token_a = await _register(client, "sos_req@example.com", "Requester A")
    await client.post(
        "/api/locations/update",
        json={"latitude": 28.7041, "longitude": 77.1025},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # 2. User B (Responder) registers nearby and updates location
    token_b = await _register(client, "sos_resp@example.com", "Responder B")
    await client.post(
        "/api/locations/update",
        json={"latitude": 28.7100, "longitude": 77.1050},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    # 3. User C (Third party) registers nearby
    token_c = await _register(client, "sos_third@example.com", "Third C")
    await client.post(
        "/api/locations/update",
        json={"latitude": 28.7110, "longitude": 77.1060},
        headers={"Authorization": f"Bearer {token_c}"},
    )

    # 4. User A creates SOS
    create_resp = await client.post(
        "/api/sos",
        json={
            "category": "VEHICLE_BREAKDOWN",
            "urgency": "HIGH",
            "description": "Flat tyre on highway, need jack and wrench",
            "latitude": 28.7041,
            "longitude": 77.1025,
            "initial_radius_m": 10000,
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_resp.status_code == 201
    sos_data = create_resp.json()
    sos_id = sos_data["id"]
    assert sos_data["status"] == "OPEN"
    assert sos_data["category"] == "VEHICLE_BREAKDOWN"

    # 5. User B checks feed, sees the SOS
    feed_resp = await client.get("/api/sos/feed", headers={"Authorization": f"Bearer {token_b}"})
    assert feed_resp.status_code == 200
    feed = feed_resp.json()
    assert any(s["id"] == sos_id for s in feed)

    # 6. User B accepts the SOS
    accept_resp = await client.post(
        f"/api/sos/{sos_id}/accept",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert accept_resp.status_code == 200
    accepted_sos = accept_resp.json()
    assert accepted_sos["status"] == "ACCEPTED"
    assert accepted_sos["responder_id"] is not None

    # 7. User C attempts to accept the SAME SOS -> MUST fail with 409 Conflict
    dup_accept_resp = await client.post(
        f"/api/sos/{sos_id}/accept",
        headers={"Authorization": f"Bearer {token_c}"},
    )
    assert dup_accept_resp.status_code == 409

    # 8. Private chat between User A and User B
    # User B sends message: "On my way with tools"
    msg1_resp = await client.post(
        f"/api/sos/{sos_id}/chat",
        json={"content": "On my way with tools, arriving in 10 mins"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert msg1_resp.status_code == 201

    # User A replies: "Thank you so much!"
    msg2_resp = await client.post(
        f"/api/sos/{sos_id}/chat",
        json={"content": "Thank you so much!"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert msg2_resp.status_code == 201

    # Verify chat history
    chat_resp = await client.get(
        f"/api/sos/{sos_id}/chat",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert chat_resp.status_code == 200
    messages = chat_resp.json()
    assert len(messages) == 2
    assert messages[0]["content"] == "On my way with tools, arriving in 10 mins"

    # 9. Non-participant User C tries to read chat -> 403 Forbidden
    forbidden_resp = await client.get(
        f"/api/sos/{sos_id}/chat",
        headers={"Authorization": f"Bearer {token_c}"},
    )
    assert forbidden_resp.status_code == 403

    # 10. User B marks SOS resolved
    resolve_resp = await client.post(
        f"/api/sos/{sos_id}/resolve",
        json={"notes": "Tyre changed successfully"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_sos_only_notifies_fresh_available_travellers(client: AsyncClient, db):
    tokens = {
        "requester": await _register(client, "eligibility-requester@example.com", "Requester"),
        "fresh": await _register(client, "eligibility-fresh@example.com", "Fresh"),
        "stale": await _register(client, "eligibility-stale@example.com", "Stale"),
        "unavailable": await _register(client, "eligibility-unavailable@example.com", "Unavailable"),
    }
    positions = {
        "requester": (28.6139, 77.2090),
        "fresh": (28.6140, 77.2090),
        "stale": (28.6141, 77.2090),
        "unavailable": (28.6142, 77.2090),
    }
    user_ids = {}
    for role, token in tokens.items():
        headers = {"Authorization": f"Bearer {token}"}
        user = await client.get("/api/me", headers=headers)
        user_ids[role] = user.json()["id"]
        latitude, longitude = positions[role]
        await client.post(
            "/api/locations/update",
            headers=headers,
            json={"latitude": latitude, "longitude": longitude},
        )

    await db.execute(
        update(UserLocation)
        .where(UserLocation.user_id == uuid.UUID(user_ids["stale"]))
        .values(updated_at=datetime.now(timezone.utc) - timedelta(minutes=10))
    )
    await db.commit()
    unavailable_profile = await client.patch(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {tokens['unavailable']}"},
        json={"is_available": False},
    )
    assert unavailable_profile.status_code == 200

    created = await client.post(
        "/api/sos",
        headers={"Authorization": f"Bearer {tokens['requester']}"},
        json={
            "category": "VEHICLE_BREAKDOWN",
            "urgency": "HIGH",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "initial_radius_m": 10000,
        },
    )
    assert created.status_code == 201
    assert any(
        event["event"] == "SOS_ALERT"
        for event in await ws_manager.recent_events(user_ids["fresh"], db)
    )
    assert await ws_manager.recent_events(user_ids["stale"], db) == []
    assert await ws_manager.recent_events(user_ids["unavailable"], db) == []
