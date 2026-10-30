"""Standardised error responses and exception handlers."""
from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    body: dict = {
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": request_id or str(uuid.uuid4()),
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code", "HTTP_ERROR")
            message = detail.get("message", str(exc.detail))
            extra = {k: v for k, v in detail.items() if k not in ("code", "message")}
        else:
            code = "HTTP_ERROR"
            message = str(detail)
            extra = {}
        return _error_response(exc.status_code, code, message, extra or None, request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        errors = exc.errors()
        details = {"fields": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in errors]}
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed",
            details,
            request_id,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        import logging
        logging.getLogger("roadlink").exception(
            "Unhandled error request_id=%s", request_id
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred",
            request_id=request_id,
        )
