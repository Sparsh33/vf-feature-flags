"""Celery application factory for the vf-feature-flags worker."""

from celery import Celery

from app.config.settings import settings


def create_celery_app() -> Celery:
    app = Celery(
        "vf_ff",
        broker=settings.celery_broker_url,
        backend=settings.celery_broker_url,
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=60 * 10,
    )
    app.autodiscover_tasks(["app.tasks"])
    return app


celery = create_celery_app()
