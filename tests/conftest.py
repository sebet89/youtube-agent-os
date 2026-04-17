from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.media import (
    MediaPreparationInput,
    PreparedMediaAsset,
)
from app.adapters.rendering import RenderInput, RenderResult
from app.api.dependencies import (
    get_content_generation_service,
    get_db_session,
    get_human_review_dashboard_service,
    get_media_asset_preparation_service,
    get_pipeline_job_service,
    get_publication_scheduler,
    get_video_rendering_service,
    get_youtube_analytics_service,
    get_youtube_oauth_service,
    get_youtube_publishing_service,
)
from app.core.security import SignedStateManager, TokenCipher
from app.db.base import Base
from app.db.models import VideoIdeaModel, VideoProjectModel, YoutubeChannelConnectionModel
from app.domain.enums import ChannelConnectionStatus, ReviewStatus, VideoVisibility
from app.main import app
from app.services.analytics import YoutubeAnalyticsService
from app.services.content_generation import (
    ContentGenerationService,
    ContentWorkflowProvider,
    GeneratedContentBundle,
    GeneratedMetadata,
)
from app.services.interfaces import (
    PublicationScheduler,
    YoutubeAnalyticsProvider,
    YoutubeCaptionUploadRequest,
    YoutubeOAuthConnection,
    YoutubePublishContext,
    YoutubeThumbnailUploadRequest,
    YoutubeVideoAnalytics,
    YoutubeVideoUploadRequest,
)
from app.services.media_assets import MediaAssetPreparationService
from app.services.oauth import YoutubeOAuthService
from app.services.pipeline import PipelineJobService, PipelineTaskDispatcher
from app.services.publishing import YoutubePublishingService
from app.services.rendering import VideoRenderingService
from app.services.review import HumanReviewDashboardService


class FakeYoutubeAuthProvider:
    def build_authorization_url(self, state: str, code_verifier: str) -> str:
        assert code_verifier
        return f"https://accounts.google.com/o/oauth2/auth?state={state}"

    def exchange_code_for_connection(
        self,
        code: str,
        code_verifier: str,
    ) -> YoutubeOAuthConnection:
        if code != "good-code":
            raise ValueError("Invalid authorization code.")
        assert code_verifier
        return YoutubeOAuthConnection(
            youtube_channel_id="UC-test-1",
            channel_title="Canal MVP",
            oauth_subject="UC-test-1",
            access_token="access-token-123",
            refresh_token="refresh-token-123",
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=[
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly",
            ],
        )


class FakeYoutubePublisher:
    def __init__(self) -> None:
        self.uploaded_requests: list[YoutubeVideoUploadRequest] = []
        self.published_video_ids: list[str] = []
        self.thumbnail_uploads: list[YoutubeThumbnailUploadRequest] = []
        self.caption_uploads: list[YoutubeCaptionUploadRequest] = []

    def upload_private_video(
        self,
        context: YoutubePublishContext,
        request: YoutubeVideoUploadRequest,
    ) -> str:
        assert context.access_token == "access-token-123"
        self.uploaded_requests.append(request)
        return "yt-uploaded-1"

    def publish_video(self, context: YoutubePublishContext, external_video_id: str) -> None:
        assert context.access_token == "access-token-123"
        self.published_video_ids.append(external_video_id)

    def upload_thumbnail(
        self,
        context: YoutubePublishContext,
        request: YoutubeThumbnailUploadRequest,
    ) -> None:
        assert context.access_token == "access-token-123"
        self.thumbnail_uploads.append(request)

    def upload_caption(
        self,
        context: YoutubePublishContext,
        request: YoutubeCaptionUploadRequest,
    ) -> None:
        assert context.access_token == "access-token-123"
        self.caption_uploads.append(request)


class FakeContentWorkflowProvider(ContentWorkflowProvider):
    def generate(self, *, video_idea: str, title_hint: str) -> GeneratedContentBundle:
        return GeneratedContentBundle(
            briefing=f"Briefing gerado para {title_hint}",
            script=f"Roteiro gerado para {video_idea}",
            metadata=GeneratedMetadata(
                title=f"{title_hint} - titulo final",
                description=f"Descricao final para {video_idea}",
                tags=["agno", "youtube", "mvp"],
                thumbnail_prompt="Thumbnail com dashboard e CTA",
            ),
            production_plan="Plano de producao final",
            workflow_name="youtube_content_pipeline",
            team_name="youtube-content-team",
            agent_names=[
                "briefing-agent",
                "script-agent",
                "metadata-agent",
                "production-agent",
            ],
        )


class FakeMediaAssetAdapter:
    def prepare_assets(self, payload: MediaPreparationInput) -> list[PreparedMediaAsset]:
        return [
            PreparedMediaAsset(
                asset_type="thumbnail",
                source_adapter="fake-media-adapter",
                source_reference=payload.thumbnail_prompt,
                storage_path=f"/tmp/{payload.project_id}/thumbnail-hero.svg",
                metadata_json={
                    "format": "svg",
                    "variant": "hero",
                    "label": "Hero forte com CTA",
                    "selected": True,
                },
            ),
            PreparedMediaAsset(
                asset_type="thumbnail",
                source_adapter="fake-media-adapter",
                source_reference=payload.thumbnail_prompt,
                storage_path=f"/tmp/{payload.project_id}/thumbnail-contrast.svg",
                metadata_json={
                    "format": "svg",
                    "variant": "contrast",
                    "label": "Contraste alto e energia",
                    "selected": False,
                },
            ),
            PreparedMediaAsset(
                asset_type="thumbnail",
                source_adapter="fake-media-adapter",
                source_reference=payload.thumbnail_prompt,
                storage_path=f"/tmp/{payload.project_id}/thumbnail-minimal.svg",
                metadata_json={
                    "format": "svg",
                    "variant": "minimal",
                    "label": "Minimalista e editorial",
                    "selected": False,
                },
            ),
            PreparedMediaAsset(
                asset_type="voiceover_script",
                source_adapter="fake-media-adapter",
                source_reference=payload.generated_script,
                storage_path=f"/tmp/{payload.project_id}/voiceover.txt",
                metadata_json={"language": "pt-BR"},
            ),
            PreparedMediaAsset(
                asset_type="voiceover_audio",
                source_adapter="fake-narration-provider",
                source_reference=payload.generated_script,
                storage_path=f"/tmp/{payload.project_id}/voiceover.wav",
                metadata_json={"language": "pt-BR", "duration_seconds": 9.5},
            ),
            PreparedMediaAsset(
                asset_type="subtitles_srt",
                source_adapter="fake-media-adapter",
                source_reference=payload.generated_script,
                storage_path=f"/tmp/{payload.project_id}/captions.srt",
                metadata_json={"language": "pt-BR", "cue_count": 3, "format": "srt"},
            ),
            PreparedMediaAsset(
                asset_type="subtitles_vtt",
                source_adapter="fake-media-adapter",
                source_reference=payload.generated_script,
                storage_path=f"/tmp/{payload.project_id}/captions.vtt",
                metadata_json={"language": "pt-BR", "cue_count": 3, "format": "vtt"},
            ),
            PreparedMediaAsset(
                asset_type="background_music",
                source_adapter="fake-media-adapter",
                source_reference=payload.generated_script,
                storage_path=f"/tmp/{payload.project_id}/background-music.wav",
                metadata_json={"duration_seconds": 9.5, "format": "wav", "mix_role": "bed"},
            ),
        ]


class FakeVideoRenderer:
    def render(self, payload: RenderInput) -> RenderResult:
        return RenderResult(
            output_path=f"/tmp/{payload.project_id}/rendered-video.mp4",
            command=["ffmpeg", "-y"],
            metadata_json={
                "renderer": "fake-renderer",
                "asset_count": len(payload.asset_paths),
                "audio_embedded": bool(payload.audio_path),
                "background_music_embedded": bool(payload.background_music_path),
            },
        )


class FakePipelineDispatcher(PipelineTaskDispatcher):
    def dispatch_project_pipeline(self, *, pipeline_job_id: str, project_id: str) -> str:
        return f"celery-{project_id}"


class FakePublicationScheduler(PublicationScheduler):
    def __init__(self) -> None:
        self.scheduled_requests: list[tuple[str, datetime]] = []
        self.cancelled_task_ids: list[str] = []

    def schedule_publication(self, *, project_id: str, publish_at: datetime) -> str:
        self.scheduled_requests.append((project_id, publish_at))
        return f"scheduled-{project_id}"

    def cancel_publication(self, *, scheduled_task_id: str) -> None:
        self.cancelled_task_ids.append(scheduled_task_id)


class FakeYoutubeAnalyticsProvider(YoutubeAnalyticsProvider):
    def fetch_video_analytics(
        self,
        context: YoutubePublishContext,
        external_video_id: str,
    ) -> YoutubeVideoAnalytics:
        assert context.access_token == "access-token-123"
        assert external_video_id == "yt-uploaded-1"
        return YoutubeVideoAnalytics(
            view_count=321,
            like_count=45,
            comment_count=6,
        )


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fake_youtube_publisher() -> FakeYoutubePublisher:
    return FakeYoutubePublisher()


@pytest.fixture
def fake_publication_scheduler() -> FakePublicationScheduler:
    return FakePublicationScheduler()


@pytest.fixture
def sample_project_id(db_session: Session) -> str:
    cipher = TokenCipher(secret_key="test-secret")
    channel = YoutubeChannelConnectionModel(
        youtube_channel_id="UC-project-channel",
        channel_title="Project Channel",
        oauth_subject="UC-project-channel",
        access_token_encrypted=cipher.encrypt("access-token-123"),
        refresh_token_encrypted=cipher.encrypt("refresh-token-123"),
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        connection_status=ChannelConnectionStatus.ACTIVE,
    )
    db_session.add(channel)
    db_session.flush()

    idea = VideoIdeaModel(
        channel_connection_id=channel.id,
        title="Ideia do projeto",
        raw_idea="Descricao base da ideia",
    )
    db_session.add(idea)
    db_session.flush()

    project = VideoProjectModel(
        idea_id=idea.id,
        generated_title="Titulo gerado",
        generated_description="Descricao gerada",
        generated_tags=["mvp", "youtube"],
        visibility=VideoVisibility.PRIVATE,
        review_status=ReviewStatus.PENDING,
    )
    db_session.add(project)
    db_session.commit()
    return project.id


@pytest.fixture
def client(
    db_session: Session,
    fake_youtube_publisher: FakeYoutubePublisher,
    fake_publication_scheduler: FakePublicationScheduler,
) -> Generator[TestClient, None, None]:
    def override_db_session() -> Generator[Session, None, None]:
        yield db_session

    def override_oauth_service() -> YoutubeOAuthService:
        return YoutubeOAuthService(
            provider=FakeYoutubeAuthProvider(),
            state_manager=SignedStateManager(secret_key="test-secret", ttl_seconds=600),
            token_cipher=TokenCipher(secret_key="test-secret"),
        )

    def override_publishing_service() -> YoutubePublishingService:
        return YoutubePublishingService(
            publisher=fake_youtube_publisher,
            token_cipher=TokenCipher(secret_key="test-secret"),
            scheduler=fake_publication_scheduler,
        )

    def override_content_generation_service() -> ContentGenerationService:
        return ContentGenerationService(provider=FakeContentWorkflowProvider())

    def override_media_asset_preparation_service() -> MediaAssetPreparationService:
        return MediaAssetPreparationService(adapter=FakeMediaAssetAdapter())

    def override_video_rendering_service() -> VideoRenderingService:
        return VideoRenderingService(
            renderer=FakeVideoRenderer(),
            output_root="/tmp/test-renders",
        )

    def override_pipeline_job_service() -> PipelineJobService:
        return PipelineJobService(dispatcher=FakePipelineDispatcher())

    def override_youtube_analytics_service() -> YoutubeAnalyticsService:
        return YoutubeAnalyticsService(
            provider=FakeYoutubeAnalyticsProvider(),
            token_cipher=TokenCipher(secret_key="test-secret"),
        )

    def override_human_review_dashboard_service() -> HumanReviewDashboardService:
        return HumanReviewDashboardService()

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_youtube_oauth_service] = override_oauth_service
    app.dependency_overrides[get_youtube_publishing_service] = override_publishing_service
    app.dependency_overrides[get_youtube_analytics_service] = override_youtube_analytics_service
    app.dependency_overrides[get_content_generation_service] = override_content_generation_service
    app.dependency_overrides[get_media_asset_preparation_service] = (
        override_media_asset_preparation_service
    )
    app.dependency_overrides[get_video_rendering_service] = override_video_rendering_service
    app.dependency_overrides[get_pipeline_job_service] = override_pipeline_job_service
    app.dependency_overrides[get_publication_scheduler] = lambda: fake_publication_scheduler
    app.dependency_overrides[get_human_review_dashboard_service] = (
        override_human_review_dashboard_service
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
