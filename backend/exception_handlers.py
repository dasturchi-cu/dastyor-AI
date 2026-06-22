"""Global API error shaping (validation + unexpected errors)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.ai_errors import AI_QUOTA_USER_MSG, AiQuotaError

logger = logging.getLogger("dastyor.api")


def _find_nested_exception(
    exc: BaseException,
    cls: type,
    *,
    _seen: set[int] | None = None,
) -> BaseException | None:
    if _seen is None:
        _seen = set()
    exc_id = id(exc)
    if exc_id in _seen:
        return None
    _seen.add(exc_id)

    if isinstance(exc, cls):
        return exc
    if isinstance(exc, BaseExceptionGroup):
        for sub in exc.exceptions:
            found = _find_nested_exception(sub, cls, _seen=_seen)
            if found is not None:
                return found
    cause = exc.__cause__
    if cause is not None:
        found = _find_nested_exception(cause, cls, _seen=_seen)
        if found is not None:
            return found
    context = exc.__context__
    if context is not None and context is not cause:
        found = _find_nested_exception(context, cls, _seen=_seen)
        if found is not None:
            return found
    return None


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"ok": False, "detail": exc.errors(), "body": "Validation error"},
        )

    @app.exception_handler(AiQuotaError)
    async def ai_quota_exception_handler(request: Request, exc: AiQuotaError):
        logger.warning("AI quota path=%s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "detail": AI_QUOTA_USER_MSG,
                "request_id": getattr(getattr(request, "state", None), "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, RuntimeError) and "No response returned" in str(exc):
            logger.exception("Middleware returned no response path=%s", request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "detail": "Server javob qaytarmadi. Qayta urinib ko'ring.",
                    "request_id": getattr(getattr(request, "state", None), "request_id", None),
                },
            )

        quota_exc = _find_nested_exception(exc, AiQuotaError)
        if quota_exc is not None:
            return await ai_quota_exception_handler(request, quota_exc)

        http_exc = _find_nested_exception(exc, HTTPException)
        if http_exc is not None:
            return JSONResponse(
                status_code=http_exc.status_code,
                content={
                    "ok": False,
                    "detail": http_exc.detail,
                    "request_id": getattr(getattr(request, "state", None), "request_id", None),
                },
                headers=getattr(http_exc, "headers", None),
            )

        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "ok": False,
                    "detail": exc.detail,
                    "request_id": getattr(getattr(request, "state", None), "request_id", None),
                },
                headers=getattr(exc, "headers", None),
            )

        logger.exception("Unhandled error path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "detail": "Internal server error",
                "request_id": getattr(getattr(request, "state", None), "request_id", None),
            },
        )
