from __future__ import annotations

from app.adapters.content_generation import AgnoContentWorkflowAdapter
from app.adapters.media import DeterministicMediaAssetAdapter
from app.adapters.narration import (
    AutoNarrationProvider,
    NarrationProvider,
    SyntheticNarrationProvider,
    WindowsSpeechNarrationProvider,
)
from app.adapters.rendering import FFmpegVideoRenderer
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.content_generation import ContentGenerationService
from app.services.media_assets import MediaAssetPreparationService
from app.services.pipeline import (
    execute_project_pipeline,
    mark_pipeline_job_failed,
    mark_pipeline_job_running,
    mark_pipeline_job_succeeded,
)
from app.services.rendering import VideoRenderingService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.pipeline.run_project_pipeline", bind=True)
def run_project_pipeline(self: object, pipeline_job_id: str, project_id: str) -> dict[str, str]:
    settings = get_settings()
    session = SessionLocal()
    synthetic_provider = SyntheticNarrationProvider()
    windows_provider = WindowsSpeechNarrationProvider(
        voice_name=settings.tts_voice_name,
        rate=settings.tts_rate,
    )
    narration_provider: NarrationProvider
    if settings.tts_provider == "windows_speech":
        narration_provider = windows_provider
    elif settings.tts_provider == "synthetic":
        narration_provider = synthetic_provider
    else:
        narration_provider = AutoNarrationProvider(
            primary=windows_provider,
            fallback=synthetic_provider,
        )
    try:
        mark_pipeline_job_running(session, pipeline_job_id)
        result = execute_project_pipeline(
            session,
            project_id=project_id,
            content_service=ContentGenerationService(
                provider=AgnoContentWorkflowAdapter(settings=settings)
            ),
            media_service=MediaAssetPreparationService(
                adapter=DeterministicMediaAssetAdapter(
                    output_root=settings.media_output_root,
                    narration_provider=narration_provider,
                )
            ),
            render_service=VideoRenderingService(
                renderer=FFmpegVideoRenderer(ffmpeg_binary=settings.ffmpeg_binary),
                output_root=settings.render_output_root,
            ),
        )
        mark_pipeline_job_succeeded(session, pipeline_job_id)
        return result
    except Exception as exc:
        mark_pipeline_job_failed(session, pipeline_job_id, error_message=str(exc))
        raise
    finally:
        session.close()
