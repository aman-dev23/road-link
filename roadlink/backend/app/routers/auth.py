"""Auth router: register, login, refresh, logout, WS ticket."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import CurrentUser
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    UserOut,
    WSTicketResponse,
)
from app.services.auth_service import AuthError, login_user, logout_user, register_user, rotate_refresh_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory WS tickets store: {ticket_hash: (user_id, expires_at)}
# Single-instance only; documented in DECISIONS.md
_ws_tickets: dict[str, tuple[str, datetime]] = {}


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, access_token, refresh_token = await register_user(
            db, body.email, body.password, body.display_name
        )
    except AuthError as e:
        status_code = status.HTTP_409_CONFLICT if e.code == "EMAIL_TAKEN" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail={"code": e.code, "message": e.message},
        )
    settings = get_settings()
    return AuthResponse(
        user=UserOut(id=str(user.id), email=user.email),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_TTL_S,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, access_token, refresh_token = await login_user(db, body.email, body.password)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )
    settings = get_settings()
    return AuthResponse(
        user=UserOut(id=str(user.id), email=user.email),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_TTL_S,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        _, access_token, new_refresh = await rotate_refresh_token(db, body.refresh_token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )
    settings = get_settings()
    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_TTL_S,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await logout_user(db, body.refresh_token)


@router.post("/ws/ticket", response_model=WSTicketResponse)
async def get_ws_ticket(current_user: CurrentUser):
    """Issue a short-lived (30s), single-use WebSocket connection ticket."""
    import hashlib
    raw = str(uuid.uuid4())
    ticket_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc).replace(microsecond=0)
    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    _ws_tickets[ticket_hash] = (str(current_user.id), expires_at)
    return WSTicketResponse(ticket=raw, expires_in=30)


def consume_ws_ticket(raw_ticket: str) -> str | None:
    """Validate and consume a WS ticket. Returns user_id or None."""
    import hashlib
    ticket_hash = hashlib.sha256(raw_ticket.encode()).hexdigest()
    entry = _ws_tickets.pop(ticket_hash, None)
    if not entry:
        return None
    user_id, expires_at = entry
    if datetime.now(timezone.utc) > expires_at:
        return None
    return user_id
