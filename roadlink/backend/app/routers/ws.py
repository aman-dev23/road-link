"""WebSocket endpoint for real-time events and chat."""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from app.deps import CurrentUser, DB
from app.schemas.auth import WSTicketResponse
from app.ws.manager import ws_manager

router = APIRouter(prefix="/api/ws", tags=["ws"])


@router.post("/ticket", response_model=WSTicketResponse)
async def create_ws_ticket(current_user: CurrentUser):
    """Issue a single-use, 30-second ticket for authenticating WebSocket connections."""
    ticket = ws_manager.issue_ticket(str(current_user.id), ttl_s=30.0)
    return WSTicketResponse(ticket=ticket, expires_in=30)


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    db: DB,
    ticket: str = Query(...),
):
    """Real-time event and messaging stream authenticated via ticket."""
    user_id = ws_manager.validate_ticket(ticket)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(user_id, websocket)
    try:
        # Send initial connected greeting
        await websocket.send_json({"event": "CONNECTED", "user_id": user_id})
        events = await ws_manager.recent_events(user_id, db)
        await db.close()
        for event in events:
            await websocket.send_json(event)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(user_id, websocket)
        await db.close()
