"""SOS router: emergency creation, nearby alerts, atomic acceptance, resolution, and chat."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, update

from app.config import get_settings
from app.deps import CurrentUser, DB
from app.models.chat import ChatMessage
from app.models.locations import UserLocation
from app.models.sos import SOSRequest
from app.models.users import User, UserProfile
from app.schemas.sos import (
    ChatMessageCreate,
    ChatMessageOut,
    SOSCancelRequest,
    SOSCreateRequest,
    SOSOut,
    SOSResolveRequest,
)
from app.services.geo import bounding_box, haversine_distance_m
from app.ws.manager import ws_manager

router = APIRouter(prefix="/api/sos", tags=["sos"])


def _to_sos_out(sos: SOSRequest, dist_m: int | None = None) -> SOSOut:
    req_profile = sos.requester.profile if sos.requester else None
    resp_profile = sos.responder.profile if sos.responder else None

    return SOSOut(
        id=str(sos.id),
        requester_id=str(sos.requester_id),
        requester_name=req_profile.display_name if req_profile else "Requester",
        requester_vehicle=req_profile.vehicle_type if req_profile else None,
        responder_id=str(sos.responder_id) if sos.responder_id else None,
        responder_name=resp_profile.display_name if resp_profile else None,
        responder_vehicle=resp_profile.vehicle_type if resp_profile else None,
        category=sos.category,
        urgency=sos.urgency,
        description=sos.description,
        latitude=sos.latitude,
        longitude=sos.longitude,
        current_radius_m=sos.current_radius_m,
        status=sos.status,
        distance_m=dist_m,
        accepted_at=sos.accepted_at,
        resolved_at=sos.resolved_at,
        cancelled_at=sos.cancelled_at,
        cancellation_reason=sos.cancellation_reason,
        created_at=sos.created_at,
        updated_at=sos.updated_at,
    )


@router.post("", response_model=SOSOut, status_code=status.HTTP_201_CREATED)
async def create_sos(body: SOSCreateRequest, current_user: CurrentUser, db: DB):
    """Create an emergency SOS request and notify eligible nearby travellers."""
    if current_user.sos_restricted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SOS_RESTRICTED", "message": "Emergency creation is restricted for this account"},
        )

    sos = SOSRequest(
        id=uuid.uuid4(),
        requester_id=current_user.id,
        category=body.category,
        urgency=body.urgency,
        description=body.description,
        latitude=body.latitude,
        longitude=body.longitude,
        current_radius_m=body.initial_radius_m,
        status="OPEN",
    )
    db.add(sos)
    await db.commit()
    await db.refresh(sos)

    # Re-fetch with requester relationship loaded
    sos_res = await db.execute(
        select(SOSRequest).where(SOSRequest.id == sos.id)
    )
    sos = sos_res.scalar_one()

    # Find nearby travellers eligible to receive SOS
    min_lat, max_lat, min_lon, max_lon = bounding_box(body.latitude, body.longitude, body.initial_radius_m)
    active_since = datetime.now(timezone.utc) - timedelta(
        seconds=get_settings().ACTIVE_WINDOW_S
    )
    stmt = (
        select(UserLocation)
        .join(User, User.id == UserLocation.user_id)
        .join(UserProfile, UserProfile.user_id == User.id)
        .where(
            UserLocation.user_id != current_user.id,
            User.status == "ACTIVE",
            UserProfile.receive_sos.is_(True),
            UserProfile.is_available.is_(True),
            UserLocation.updated_at >= active_since,
            UserLocation.latitude >= min_lat,
            UserLocation.latitude <= max_lat,
            UserLocation.longitude >= min_lon,
            UserLocation.longitude <= max_lon,
        )
    )
    res = await db.execute(stmt)
    candidate_locs = res.scalars().all()

    recipient_ids: list[str] = []
    for cloc in candidate_locs:
        dist = haversine_distance_m(body.latitude, body.longitude, cloc.latitude, cloc.longitude)
        if dist <= body.initial_radius_m:
            recipient_ids.append(str(cloc.user_id))

    out = _to_sos_out(sos)
    # Broadcast real-time SOS event
    if recipient_ids:
        await ws_manager.broadcast_to_users(
            recipient_ids,
            {"event": "SOS_ALERT", "sos": out.model_dump(mode="json")},
            db,
        )

    return out


@router.get("/active", response_model=list[SOSOut])
async def get_my_active_sos(current_user: CurrentUser, db: DB):
    """Get active SOS where caller is requester or responder."""
    stmt = (
        select(SOSRequest)
        .where(
            (SOSRequest.requester_id == current_user.id) | (SOSRequest.responder_id == current_user.id),
            SOSRequest.status.in_(["OPEN", "ACCEPTED"]),
        )
        .order_by(SOSRequest.created_at.desc())
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [_to_sos_out(item) for item in items]


@router.get("/feed", response_model=list[SOSOut])
async def get_sos_feed(
    current_user: CurrentUser,
    db: DB,
    latitude: float | None = Query(default=None, ge=-90.0, le=90.0),
    longitude: float | None = Query(default=None, ge=-180.0, le=180.0),
    radius_m: int = Query(default=50000, ge=1000, le=200000),
):
    """Get incoming OPEN emergency SOS requests within range of the caller."""
    ref_lat = latitude
    ref_lon = longitude
    if ref_lat is None or ref_lon is None:
        my_loc = await db.execute(
            select(UserLocation).where(UserLocation.user_id == current_user.id)
        )
        loc = my_loc.scalar_one_or_none()
        if loc:
            ref_lat = loc.latitude
            ref_lon = loc.longitude

    stmt = (
        select(SOSRequest)
        .where(
            SOSRequest.status == "OPEN",
            SOSRequest.requester_id != current_user.id,
        )
        .order_by(SOSRequest.created_at.desc())
    )
    res = await db.execute(stmt)
    requests = res.scalars().all()

    feed: list[SOSOut] = []
    for sos in requests:
        dist_m = None
        if ref_lat is not None and ref_lon is not None:
            dist_m = int(haversine_distance_m(ref_lat, ref_lon, sos.latitude, sos.longitude))
            # Check if within SOS broadcast radius
            if dist_m > max(sos.current_radius_m, radius_m):
                continue
        feed.append(_to_sos_out(sos, dist_m=dist_m))

    feed.sort(key=lambda s: s.distance_m if s.distance_m is not None else 0)
    return feed


@router.get("/{sos_id}", response_model=SOSOut)
async def get_sos_detail(sos_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Fetch details of a single SOS request."""
    res = await db.execute(
        select(SOSRequest).where(SOSRequest.id == sos_id)
    )
    sos = res.scalar_one_or_none()
    if not sos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Emergency request not found"},
        )
    return _to_sos_out(sos)


@router.post("/{sos_id}/accept", response_model=SOSOut)
async def accept_sos(sos_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """
    Atomically accept an open SOS request.
    Prevents race conditions by using a single conditional atomic update query.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        update(SOSRequest)
        .where(
            SOSRequest.id == sos_id,
            SOSRequest.status == "OPEN",
            SOSRequest.requester_id != current_user.id,
        )
        .values(
            status="ACCEPTED",
            responder_id=current_user.id,
            accepted_at=now,
            updated_at=now,
        )
    )
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount == 0:
        # Check why it couldn't be accepted
        check = await db.execute(select(SOSRequest).where(SOSRequest.id == sos_id))
        sos_item = check.scalar_one_or_none()
        if not sos_item:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "SOS not found"})
        if sos_item.requester_id == current_user.id:
            raise HTTPException(status_code=400, detail={"code": "CANNOT_ACCEPT_OWN", "message": "You cannot accept your own SOS"})
        if sos_item.status != "OPEN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "ALREADY_ACCEPTED", "message": "This emergency has already been accepted or closed"},
            )
        raise HTTPException(status_code=400, detail={"code": "ACCEPT_FAILED", "message": "Could not accept SOS"})

    # Fetch updated record
    fresh = await db.execute(select(SOSRequest).where(SOSRequest.id == sos_id))
    sos = fresh.scalar_one()
    out = _to_sos_out(sos)

    # Real-time notification to requester
    await ws_manager.send_to_user(
        str(sos.requester_id),
        {"event": "SOS_ACCEPTED", "sos": out.model_dump(mode="json")},
        db,
    )

    return out


@router.post("/{sos_id}/resolve", response_model=SOSOut)
async def resolve_sos(
    sos_id: uuid.UUID,
    body: SOSResolveRequest,
    current_user: CurrentUser,
    db: DB,
):
    """Mark an accepted SOS as resolved (caller must be requester or responder)."""
    now = datetime.now(timezone.utc)
    stmt = (
        update(SOSRequest)
        .where(
            SOSRequest.id == sos_id,
            SOSRequest.status == "ACCEPTED",
            (SOSRequest.requester_id == current_user.id) | (SOSRequest.responder_id == current_user.id),
        )
        .values(
            status="RESOLVED",
            resolved_at=now,
            updated_at=now,
        )
    )
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "RESOLVE_FAILED", "message": "SOS cannot be resolved (must be ACCEPTED and you must be participant)"},
        )

    fresh = await db.execute(select(SOSRequest).where(SOSRequest.id == sos_id))
    sos = fresh.scalar_one()
    out = _to_sos_out(sos)

    # Notify other participant
    other_id = str(sos.responder_id if current_user.id == sos.requester_id else sos.requester_id)
    if other_id:
        await ws_manager.send_to_user(
            other_id, {"event": "SOS_RESOLVED", "sos": out.model_dump(mode="json")}, db
        )

    return out


@router.post("/{sos_id}/cancel", response_model=SOSOut)
async def cancel_sos(
    sos_id: uuid.UUID,
    body: SOSCancelRequest,
    current_user: CurrentUser,
    db: DB,
):
    """Cancel an open or accepted SOS (requester only)."""
    now = datetime.now(timezone.utc)
    stmt = (
        update(SOSRequest)
        .where(
            SOSRequest.id == sos_id,
            SOSRequest.requester_id == current_user.id,
            SOSRequest.status.in_(["OPEN", "ACCEPTED"]),
        )
        .values(
            status="CANCELLED",
            cancelled_at=now,
            cancellation_reason=body.reason,
            updated_at=now,
        )
    )
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CANCEL_FAILED", "message": "SOS cannot be cancelled or caller is not requester"},
        )

    fresh = await db.execute(select(SOSRequest).where(SOSRequest.id == sos_id))
    sos = fresh.scalar_one()
    out = _to_sos_out(sos)

    # If responder had accepted, notify responder
    if sos.responder_id:
        await ws_manager.send_to_user(
            str(sos.responder_id),
            {"event": "SOS_CANCELLED", "sos": out.model_dump(mode="json")},
            db,
        )

    return out


@router.get("/{sos_id}/chat", response_model=list[ChatMessageOut])
async def get_sos_chat_history(sos_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Fetch chat message history for an emergency (requester or responder only)."""
    sos_res = await db.execute(select(SOSRequest).where(SOSRequest.id == sos_id))
    sos = sos_res.scalar_one_or_none()
    if not sos:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "SOS not found"})

    if current_user.id not in (sos.requester_id, sos.responder_id):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Not a participant in this SOS"})

    stmt = (
        select(ChatMessage)
        .where(ChatMessage.sos_id == sos_id)
        .order_by(ChatMessage.created_at.asc())
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()

    return [
        ChatMessageOut(
            id=str(m.id),
            sos_id=str(m.sos_id),
            sender_id=str(m.sender_id),
            sender_name=m.sender.profile.display_name if (m.sender and m.sender.profile) else "User",
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/{sos_id}/chat", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def post_sos_chat_message(
    sos_id: uuid.UUID,
    body: ChatMessageCreate,
    current_user: CurrentUser,
    db: DB,
):
    """Send a private message between requester and responder."""
    sos_res = await db.execute(select(SOSRequest).where(SOSRequest.id == sos_id))
    sos = sos_res.scalar_one_or_none()
    if not sos:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "SOS not found"})

    if current_user.id not in (sos.requester_id, sos.responder_id):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Not a participant in this SOS"})

    if sos.status not in ("OPEN", "ACCEPTED"):
        raise HTTPException(status_code=400, detail={"code": "SOS_CLOSED", "message": "Cannot send messages in a closed SOS"})

    msg = ChatMessage(
        id=uuid.uuid4(),
        sos_id=sos_id,
        sender_id=current_user.id,
        content=body.content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Re-fetch with sender joined
    msg_res = await db.execute(select(ChatMessage).where(ChatMessage.id == msg.id))
    msg = msg_res.scalar_one()

    out = ChatMessageOut(
        id=str(msg.id),
        sos_id=str(msg.sos_id),
        sender_id=str(msg.sender_id),
        sender_name=current_user.profile.display_name if current_user.profile else "User",
        content=msg.content,
        created_at=msg.created_at,
    )

    # Broadcast to other party
    other_party = str(sos.responder_id if current_user.id == sos.requester_id else sos.requester_id)
    if other_party:
        await ws_manager.send_to_user(
            other_party,
            {"event": "CHAT_MESSAGE", "message": out.model_dump(mode="json")},
            db,
        )

    return out
