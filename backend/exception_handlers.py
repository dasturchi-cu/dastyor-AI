"""Global API error shaping (validation + unexpected errors)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("dastyor.api")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"ok": False, "detail": exc.errors(), "body": "Validation error"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        from fastapi import HTTPException

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
