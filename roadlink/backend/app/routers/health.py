"""Health check router."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/deep")
async def health_deep():
    settings = get_settings()
    db_ok = False
    postgis_ok = False
    try:
        from sqlalchemy.ext.asyncio import AsyncConnection
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
            try:
                result = await conn.execute(
                    text("SELECT PostGIS_Version()")
                )
                _ = result.scalar()
                postgis_ok = True
            except Exception:
                postgis_ok = False
    except Exception:
        db_ok = False

    ai_status = "disabled"
    if settings.AI_PROVIDER == "ollama":
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                ai_status = "ok" if resp.status_code == 200 else "down"
        except Exception:
            ai_status = "down"

    return {
        "db": db_ok,
        "postgis": postgis_ok,
        "ai": ai_status,
        "places": "ok",
        "workers": {},
    }
