"""WebSocket connection manager and event dispatcher."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import NotificationEvent

_EVENT_HISTORY_SIZE = 50
_EVENT_HISTORY_TTL_S = 1800


class ConnectionManager:
    def __init__(self):
        # Maps user_id to list of active WebSockets
        self._active_connections: dict[str, list[WebSocket]] = {}
        # Ticket store: {ticket: (user_id, expires_at)}
        self._tickets: dict[str, tuple[str, float]] = {}

    def issue_ticket(self, user_id: str, ttl_s: float = 30.0) -> str:
        ticket = str(uuid.uuid4())
        self._tickets[ticket] = (user_id, datetime.now(timezone.utc).timestamp() + ttl_s)
        return ticket

    def validate_ticket(self, ticket: str) -> str | None:
        """Validate single-use ticket and return user_id, or None if invalid/expired."""
        self._cleanup_expired_tickets()
        if ticket not in self._tickets:
            return None
        user_id, expires_at = self._tickets.pop(ticket)
        if datetime.now(timezone.utc).timestamp() > expires_at:
            return None
        return user_id

    def _cleanup_expired_tickets(self):
        now = datetime.now(timezone.utc).timestamp()
        expired = [t for t, (_, exp) in self._tickets.items() if now > exp]
        for t in expired:
            self._tickets.pop(t, None)

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self._active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self._active_connections:
            try:
                self._active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self._active_connections[user_id]:
                del self._active_connections[user_id]

    async def recent_events(
        self, user_id: str, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Return this user's recent persisted events in delivery order."""
        cutoff = datetime.now(timezone.utc).timestamp() - _EVENT_HISTORY_TTL_S
        cutoff_at = datetime.fromtimestamp(cutoff, timezone.utc)
        result = await db.execute(
            select(NotificationEvent.payload)
            .where(
                NotificationEvent.user_id == uuid.UUID(user_id),
                NotificationEvent.created_at >= cutoff_at,
            )
            .order_by(
                NotificationEvent.created_at.desc(),
                NotificationEvent.event_id.desc(),
            )
            .limit(_EVENT_HISTORY_SIZE)
        )
        return [payload for payload, in reversed(result.all())]

    async def send_to_user(
        self, user_id: str, message: dict[str, Any], db: AsyncSession
    ):
        event = message.copy()
        event.setdefault("event_id", str(uuid.uuid4()))
        db.add(
            NotificationEvent(
                event_id=uuid.UUID(event["event_id"]),
                user_id=uuid.UUID(user_id),
                payload=event,
                created_at=datetime.now(timezone.utc),
            )
        )
        await db.flush()
        expired = datetime.now(timezone.utc).timestamp() - _EVENT_HISTORY_TTL_S
        await db.execute(
            delete(NotificationEvent).where(
                NotificationEvent.created_at < datetime.fromtimestamp(expired, timezone.utc)
            )
        )
        excess = (
            select(NotificationEvent.event_id)
            .where(NotificationEvent.user_id == uuid.UUID(user_id))
            .order_by(
                NotificationEvent.created_at.desc(),
                NotificationEvent.event_id.desc(),
            )
            .offset(_EVENT_HISTORY_SIZE)
        )
        await db.execute(
            delete(NotificationEvent).where(NotificationEvent.event_id.in_(excess))
        )
        await db.commit()

        if user_id in self._active_connections:
            payload = json.dumps(event)
            dead_sockets = []
            for ws in list(self._active_connections[user_id]):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead_sockets.append(ws)
            for ws in dead_sockets:
                self.disconnect(user_id, ws)

    async def broadcast_to_users(
        self, user_ids: list[str], message: dict[str, Any], db: AsyncSession
    ):
        for user_id in user_ids:
            await self.send_to_user(user_id, message, db)

    def is_user_online(self, user_id: str) -> bool:
        return bool(self._active_connections.get(user_id))


ws_manager = ConnectionManager()
