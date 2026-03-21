from __future__ import annotations

from fastapi import HTTPException, Request


def get_ptb_application(request: Request):
    ptb = getattr(request.app.state, "ptb_application", None)
    if ptb is None:
        raise HTTPException(status_code=503, detail="Telegram bot application is not initialized")
    return ptb
