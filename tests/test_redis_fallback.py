"""Redis fallback — sessions, voice jobs, rate limit work without Redis."""
from __future__ import annotations

import os

os.environ["USE_REDIS"] = "0"

import pytest
from fastapi import Request
from starlette.datastructures import Address

from core import redis_client
from core.security import rate_limit
from shared import session_service, voice_jobs


@pytest.fixture(autouse=True)
def _reset_redis_state():
    redis_client.close_sync()
    redis_client._redis_checked = False
    redis_client._redis_ok = False
    yield
    redis_client.close_sync()


def test_redis_disabled_by_default():
    assert not redis_client.redis_enabled() or os.environ.get("USE_REDIS") == "0"


def test_session_file_fallback():
    token = session_service.create_session(111222, "Test", "testuser", "")
    sess = session_service.resolve_session(token)
    assert sess is not None
    assert sess["telegram_id"] == "111222"
    assert session_service.resolve_telegram_id(token) == "111222"


def test_voice_job_memory_fallback():
    job_id = voice_jobs.create_job(333444, "cv")
    voice_jobs.set_step(job_id, 2, status="running")
    voice_jobs.complete_job(job_id, {"name": "Ali"}, [], 80, "transcript")
    job = voice_jobs.get_job(job_id, 333444)
    assert job is not None
    assert job["status"] == "done"
    assert job["data"]["name"] == "Ali"
    assert voice_jobs.get_job(job_id, 999) is None


def test_rate_limit_memory_fallback():
    import asyncio
    from unittest.mock import patch

    class _App:
        state = type("S", (), {})()

    req = Request(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "app": _App(),
        }
    )
    req._url = type("U", (), {"path": "/"})()
    req._client = Address("127.0.0.1", 12345)

    async def _run():
        with patch("core.security.settings") as mock_settings:
            mock_settings.rate_limit_per_minute = 100
            for _ in range(5):
                await rate_limit(req, key="test-client-fallback")

    asyncio.run(_run())
