from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("youtube_agent_os", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True
celery_app.conf.task_default_queue = "pipeline"
celery_app.conf.imports = ("app.tasks.pipeline", "app.tasks.publishing")
