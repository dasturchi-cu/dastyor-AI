from __future__ import annotations

from celery import Celery

from backend.settings import get_settings


def make_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "dastyor_ai",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["backend.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        task_track_started=True,
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = make_celery()

