from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    AnalyticsSnapshotModel,
    MediaAssetModel,
    PipelineJobModel,
    PublicationReviewModel,
    VideoIdeaModel,
    VideoProjectModel,
    WorkflowRunModel,
    YoutubeChannelConnectionModel,
)
from app.domain.enums import (
    ChannelConnectionStatus,
    JobStatus,
    MediaAssetStatus,
    ReviewStatus,
    VideoIdeaStatus,
    VideoVisibility,
)


def build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return session_factory()


def test_persists_project_aggregate_with_related_records() -> None:
    session = build_session()

    channel = YoutubeChannelConnectionModel(
        youtube_channel_id="UC123",
        channel_title="Test Channel",
        connection_status=ChannelConnectionStatus.ACTIVE,
        scopes=["youtube.upload"],
    )
    session.add(channel)
    session.flush()

    idea = VideoIdeaModel(
        channel_connection_id=channel.id,
        title="Como automatizar um canal",
        raw_idea="Criar um tutorial do produto",
        target_audience="Criadores de conteudo",
        business_goal="Demonstrar o MVP",
        status=VideoIdeaStatus.DRAFT,
    )
    session.add(idea)
    session.flush()

    project = VideoProjectModel(
        idea_id=idea.id,
        generated_briefing="Briefing inicial",
        generated_script="Roteiro inicial",
        generated_title="Automatize seu canal",
        generated_description="Descricao gerada",
        generated_tags=["youtube", "automacao"],
        thumbnail_prompt="Thumbnail clean com CTA",
        production_plan="Gravar intro e demo",
        visibility=VideoVisibility.PRIVATE,
        review_status=ReviewStatus.PENDING,
    )
    session.add(project)
    session.flush()

    session.add_all(
        [
            MediaAssetModel(
                project_id=project.id,
                asset_type="thumbnail",
                source_adapter="image-generator",
                source_reference="thumb://briefing/1",
                storage_path="/tmp/thumb.png",
                status=MediaAssetStatus.READY,
                metadata_json={"format": "png"},
            ),
            PipelineJobModel(
                project_id=project.id,
                job_type="render_video",
                queue_name="render",
                status=JobStatus.SUCCEEDED,
                celery_task_id="celery-123",
            ),
            WorkflowRunModel(
                project_id=project.id,
                workflow_name="content_pipeline",
                status=JobStatus.SUCCEEDED,
                input_payload={"video_idea_id": idea.id},
                output_payload={"project_id": project.id},
            ),
            PublicationReviewModel(
                project_id=project.id,
                reviewer_name="reviewer@example.com",
                status=ReviewStatus.APPROVED,
                notes="Aprovado para publicacao",
            ),
            AnalyticsSnapshotModel(
                project_id=project.id,
                youtube_video_id="yt-video-1",
                view_count=42,
                like_count=7,
                comment_count=3,
            ),
        ]
    )
    session.commit()

    persisted_project = session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == project.id)
    )

    assert persisted_project is not None
    assert persisted_project.idea.title == "Como automatizar um canal"
    assert persisted_project.visibility == VideoVisibility.PRIVATE
    assert persisted_project.review_status == ReviewStatus.PENDING
    assert len(persisted_project.media_assets) == 1
    assert len(persisted_project.jobs) == 1
    assert len(persisted_project.workflow_runs) == 1
    assert len(persisted_project.publication_reviews) == 1
    assert len(persisted_project.analytics_snapshots) == 1
    assert persisted_project.media_assets[0].status == MediaAssetStatus.READY
    assert persisted_project.jobs[0].status == JobStatus.SUCCEEDED
    assert persisted_project.publication_reviews[0].status == ReviewStatus.APPROVED

    persisted_channel = session.scalar(
        select(YoutubeChannelConnectionModel).where(
            YoutubeChannelConnectionModel.id == channel.id
        )
    )
    assert persisted_channel is not None
    assert persisted_channel.video_ideas[0].project is not None
    assert persisted_channel.video_ideas[0].project.generated_tags == ["youtube", "automacao"]
