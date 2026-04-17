from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.content_generation import AgnoContentWorkflowAdapter
from app.adapters.google_cloud_media import (
    GoogleCloudMediaSettings,
    GoogleCloudTTSNarrationProvider,
    VertexAIImagenThumbnailGenerator,
    VertexAIVeoVideoRenderer,
)
from app.adapters.media import DeterministicMediaAssetAdapter
from app.adapters.narration import (
    AutoNarrationProvider,
    EdgeTTSNarrationProvider,
    NarrationProvider,
    SyntheticNarrationProvider,
    WindowsSpeechNarrationProvider,
)
from app.adapters.rendering import FFmpegVideoRenderer, VideoRenderer
from app.adapters.youtube_analytics import GoogleYoutubeAnalyticsAdapter
from app.adapters.youtube_oauth import GoogleYoutubeOAuthAdapter
from app.adapters.youtube_publisher import GoogleYoutubePublisherAdapter
from app.core.config import Settings, get_settings
from app.core.security import SignedStateManager, TokenCipher
from app.db.session import SessionLocal
from app.services.analytics import YoutubeAnalyticsService
from app.services.content_generation import (
    ContentGenerationService,
    ContentWorkflowProvider,
)
from app.services.interfaces import YoutubeAnalyticsProvider, YoutubeAuthProvider, YoutubePublisher
from app.services.media_assets import MediaAssetPreparationService
from app.services.oauth import YoutubeOAuthService
from app.services.pipeline import PipelineJobService, PipelineTaskDispatcher
from app.services.project_actions import ProjectPreparationService
from app.services.project_editing import ProjectEditingService
from app.services.projects import ProjectCreationService
from app.services.publishing import YoutubePublishingService
from app.services.rendering import VideoRenderingService
from app.services.review import HumanReviewDashboardService
from app.services.studio import StudioDashboardService
from app.services.system_settings import SystemSettingsService
from app.tasks.celery_app import celery_app


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_settings() -> Settings:
    return get_settings()


def get_signed_state_manager(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> SignedStateManager:
    return SignedStateManager(
        secret_key=settings.secret_key,
        ttl_seconds=settings.youtube_oauth_state_ttl_seconds,
    )


def get_token_cipher(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> TokenCipher:
    return TokenCipher(secret_key=settings.secret_key)


def get_youtube_auth_provider(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> GoogleYoutubeOAuthAdapter:
    return GoogleYoutubeOAuthAdapter(settings=settings)


def get_youtube_publisher(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> GoogleYoutubePublisherAdapter:
    return GoogleYoutubePublisherAdapter(settings=settings)


def get_youtube_analytics_provider(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> GoogleYoutubeAnalyticsAdapter:
    return GoogleYoutubeAnalyticsAdapter(settings=settings)


def get_content_workflow_provider(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> AgnoContentWorkflowAdapter:
    return AgnoContentWorkflowAdapter(settings=settings)


def get_narration_provider(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> NarrationProvider:
    synthetic_provider = SyntheticNarrationProvider()
    edge_provider = EdgeTTSNarrationProvider(
        voice_name=settings.tts_voice_name,
        rate=settings.tts_rate,
    )
    windows_provider = WindowsSpeechNarrationProvider(
        voice_name=settings.tts_voice_name,
        rate=settings.tts_rate,
    )
    google_tts_provider = _build_google_tts_provider(settings)
    if settings.tts_provider == "google_cloud":
        if google_tts_provider is None:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT must be configured to use TTS_PROVIDER=google_cloud."
            )
        return google_tts_provider
    if settings.tts_provider == "edge_tts":
        return edge_provider
    if settings.tts_provider == "windows_speech":
        return windows_provider
    if settings.tts_provider == "synthetic":
        return synthetic_provider
    auto_fallback = AutoNarrationProvider(
        primary=edge_provider,
        fallback=AutoNarrationProvider(
            primary=windows_provider,
            fallback=synthetic_provider,
        ),
    )
    if google_tts_provider is None:
        return auto_fallback
    return AutoNarrationProvider(
        primary=google_tts_provider,
        fallback=auto_fallback,
    )


def get_video_renderer(
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> VideoRenderer:
    if settings.video_provider == "vertex_veo":
        return VertexAIVeoVideoRenderer(settings=_build_google_cloud_media_settings(settings))
    return FFmpegVideoRenderer(ffmpeg_binary=settings.ffmpeg_binary)


def get_media_asset_preparation_service(
    settings: Annotated[Settings, Depends(get_current_settings)],
    narration_provider: Annotated[NarrationProvider, Depends(get_narration_provider)],
) -> MediaAssetPreparationService:
    thumbnail_generator = None
    if settings.thumbnail_provider == "vertex_imagen":
        thumbnail_generator = VertexAIImagenThumbnailGenerator(
            settings=_build_google_cloud_media_settings(settings)
        )
    adapter = DeterministicMediaAssetAdapter(
        output_root=settings.media_output_root,
        narration_provider=narration_provider,
        thumbnail_generator=thumbnail_generator,
    )
    return MediaAssetPreparationService(adapter=adapter)


def _build_google_tts_provider(settings: Settings) -> GoogleCloudTTSNarrationProvider | None:
    if not settings.google_cloud_project:
        return None
    return GoogleCloudTTSNarrationProvider(settings=_build_google_cloud_media_settings(settings))


def _build_google_cloud_media_settings(settings: Settings) -> GoogleCloudMediaSettings:
    project_id = settings.google_cloud_project or ""
    if not project_id:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT must be configured to use Google Cloud media providers."
        )
    return GoogleCloudMediaSettings(
        project_id=project_id,
        location=settings.google_cloud_location,
        imagen_model=settings.vertex_imagen_model,
        veo_model=settings.vertex_veo_model,
        veo_aspect_ratio=settings.vertex_veo_aspect_ratio,
        veo_resolution=settings.vertex_veo_resolution,
        veo_duration_seconds=settings.vertex_veo_duration_seconds,
        veo_generate_audio=settings.vertex_veo_generate_audio,
        tts_voice_name=settings.google_tts_voice_name,
        tts_language_code=settings.google_tts_language_code,
        tts_speaking_rate=settings.google_tts_speaking_rate,
    )


def get_video_rendering_service(
    renderer: Annotated[VideoRenderer, Depends(get_video_renderer)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> VideoRenderingService:
    return VideoRenderingService(renderer=renderer, output_root=settings.render_output_root)


def get_project_preparation_service(
    content_service: Annotated[ContentGenerationService, Depends(get_content_generation_service)],
    media_service: Annotated[
        MediaAssetPreparationService, Depends(get_media_asset_preparation_service)
    ],
    render_service: Annotated[VideoRenderingService, Depends(get_video_rendering_service)],
) -> ProjectPreparationService:
    return ProjectPreparationService(
        content_service=content_service,
        media_service=media_service,
        render_service=render_service,
    )


class CeleryPipelineDispatcher(PipelineTaskDispatcher):
    def dispatch_project_pipeline(self, *, pipeline_job_id: str, project_id: str) -> str:
        async_result = celery_app.send_task(
            "app.tasks.pipeline.run_project_pipeline",
            args=[pipeline_job_id, project_id],
            queue="pipeline",
        )
        return str(async_result.id)


class CeleryPublicationScheduler:
    def schedule_publication(self, *, project_id: str, publish_at: datetime) -> str:
        async_result = celery_app.send_task(
            "app.tasks.publishing.publish_project_on_schedule",
            args=[project_id],
            eta=publish_at,
            queue="pipeline",
        )
        return str(async_result.id)

    def cancel_publication(self, *, scheduled_task_id: str) -> None:
        celery_app.control.revoke(scheduled_task_id, terminate=False)


def get_publication_scheduler() -> CeleryPublicationScheduler:
    return CeleryPublicationScheduler()


def get_youtube_oauth_service(
    provider: Annotated[YoutubeAuthProvider, Depends(get_youtube_auth_provider)],
    state_manager: Annotated[SignedStateManager, Depends(get_signed_state_manager)],
    token_cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
) -> YoutubeOAuthService:
    return YoutubeOAuthService(
        provider=provider,
        state_manager=state_manager,
        token_cipher=token_cipher,
    )


def get_youtube_publishing_service(
    publisher: Annotated[YoutubePublisher, Depends(get_youtube_publisher)],
    token_cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
    scheduler: Annotated[CeleryPublicationScheduler, Depends(get_publication_scheduler)],
) -> YoutubePublishingService:
    return YoutubePublishingService(
        publisher=publisher,
        token_cipher=token_cipher,
        scheduler=scheduler,
    )


def get_youtube_analytics_service(
    provider: Annotated[YoutubeAnalyticsProvider, Depends(get_youtube_analytics_provider)],
    token_cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
) -> YoutubeAnalyticsService:
    return YoutubeAnalyticsService(provider=provider, token_cipher=token_cipher)


def get_content_generation_service(
    provider: Annotated[ContentWorkflowProvider, Depends(get_content_workflow_provider)],
) -> ContentGenerationService:
    return ContentGenerationService(provider=provider)




def get_pipeline_task_dispatcher() -> CeleryPipelineDispatcher:
    return CeleryPipelineDispatcher()


def get_pipeline_job_service(
    dispatcher: Annotated[PipelineTaskDispatcher, Depends(get_pipeline_task_dispatcher)],
) -> PipelineJobService:
    return PipelineJobService(dispatcher=dispatcher)


def get_human_review_dashboard_service() -> HumanReviewDashboardService:
    return HumanReviewDashboardService()


def get_project_creation_service() -> ProjectCreationService:
    return ProjectCreationService()


def get_project_editing_service() -> ProjectEditingService:
    return ProjectEditingService()


def get_studio_dashboard_service() -> StudioDashboardService:
    return StudioDashboardService()


def get_system_settings_service() -> SystemSettingsService:
    return SystemSettingsService()
