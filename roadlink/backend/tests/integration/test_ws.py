"""Integration tests for WebSocket ticket authentication."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.ws.manager import ConnectionManager


@pytest.mark.asyncio
async def test_offline_events_are_available_for_reconnect(db):
    manager = ConnectionManager()

    from app.models.users import User

    user_a = User(email="a@example.com", password_hash="hash")
    user_b = User(email="b@example.com", password_hash="hash")
    db.add_all([user_a, user_b])
    await db.commit()

    await manager.send_to_user(str(user_a.id), {"event": "SOS_ALERT", "sos": {"id": "1"}}, db)
    await manager.send_to_user(str(user_b.id), {"event": "SOS_ALERT", "sos": {"id": "2"}}, db)

    reconnecting_worker = ConnectionManager()
    events = await reconnecting_worker.recent_events(str(user_a.id), db)
    assert len(events) == 1
    assert events[0]["event"] == "SOS_ALERT"
    assert events[0]["sos"]["id"] == "1"
    assert events[0]["event_id"]
    assert (await reconnecting_worker.recent_events(str(user_b.id), db))[0]["sos"]["id"] == "2"


@pytest.mark.asyncio
async def test_reconnect_history_is_bounded(db):
    manager = ConnectionManager()
    from app.models.users import User

    user = User(email="bounded@example.com", password_hash="hash")
    db.add(user)
    await db.commit()

    for index in range(55):
        await manager.send_to_user(
            str(user.id), {"event": "CHAT_MESSAGE", "index": index}, db
        )

    events = await manager.recent_events(str(user.id), db)
    assert len(events) == 50
    assert events[0]["index"] == 5
    assert events[-1]["index"] == 54


@pytest.mark.asyncio
async def test_ws_ticket_flow(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "wstest@example.com",
        "password": "password123",
        "display_name": "WS User",
    })
    token = reg.json()["access_token"]

    # Request a ticket
    ticket_resp = await client.post(
        "/api/ws/ticket",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ticket_resp.status_code == 200
    data = ticket_resp.json()
    assert "ticket" in data
    assert data["expires_in"] == 30
