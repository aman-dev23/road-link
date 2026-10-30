"""FastAPI application entry point."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.errors import register_exception_handlers
from app.routers import auth, me, health, config as config_router, locations, sos, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown tasks."""
    settings = get_settings()
    await init_db()
    if "sqlite" in settings.DATABASE_URL:
        from app.db import Base, get_engine
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: close connections
    from app.db import _engine
    if _engine:
        await _engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="RoadLink API",
        version=settings.APP_VERSION,
        description="You're never alone on the road.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Security headers
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    # Exception handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(auth.router)
    app.include_router(ws.router)
    app.include_router(me.router)
    app.include_router(locations.router)
    app.include_router(sos.router)
    app.include_router(health.router)
    app.include_router(config_router.router)

    return app


app = create_app()
