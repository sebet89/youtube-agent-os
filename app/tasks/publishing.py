from __future__ import annotations

from app.adapters.youtube_publisher import GoogleYoutubePublisherAdapter
from app.core.config import get_settings
from app.core.security import TokenCipher
from app.db.session import SessionLocal
from app.services.publishing import YoutubePublishingService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.publishing.publish_project_on_schedule", bind=True)
def publish_project_on_schedule(self: object, project_id: str) -> dict[str, str]:
    settings = get_settings()
    session = SessionLocal()
    try:
        service = YoutubePublishingService(
            publisher=GoogleYoutubePublisherAdapter(settings=settings),
            token_cipher=TokenCipher(secret_key=settings.secret_key),
        )
        result = service.execute_scheduled_publication(
            session,
            project_id=project_id,
            task_id=str(getattr(getattr(self, "request", None), "id", "") or ""),
        )
        return {
            "project_id": result.project_id,
            "youtube_video_id": result.youtube_video_id,
            "visibility": result.visibility,
        }
    finally:
        session.close()
