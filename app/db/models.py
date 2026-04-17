from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    ChannelConnectionStatus,
    JobStatus,
    MediaAssetStatus,
    ReviewStatus,
    VideoIdeaStatus,
    VideoVisibility,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def default_uuid() -> str:
    return str(uuid4())


class YoutubeChannelConnectionModel(Base):
    __tablename__ = "youtube_channel_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    youtube_channel_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    channel_title: Mapped[str] = mapped_column(String(255))
    oauth_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scopes: Mapped[list[str]] = mapped_column(JSON(), default=list)
    connection_status: Mapped[ChannelConnectionStatus] = mapped_column(
        Enum(ChannelConnectionStatus),
        default=ChannelConnectionStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    video_ideas: Mapped[list[VideoIdeaModel]] = relationship(back_populates="channel_connection")


class VideoIdeaModel(Base):
    __tablename__ = "video_ideas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    channel_connection_id: Mapped[str] = mapped_column(
        ForeignKey("youtube_channel_connections.id"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    raw_idea: Mapped[str] = mapped_column(Text())
    target_audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[VideoIdeaStatus] = mapped_column(
        Enum(VideoIdeaStatus),
        default=VideoIdeaStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    channel_connection: Mapped[YoutubeChannelConnectionModel] = relationship(
        back_populates="video_ideas"
    )
    project: Mapped[VideoProjectModel] = relationship(back_populates="idea", uselist=False)


class VideoProjectModel(Base):
    __tablename__ = "video_projects"
    __table_args__ = (UniqueConstraint("idea_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    idea_id: Mapped[str] = mapped_column(ForeignKey("video_ideas.id"), index=True)
    generated_briefing: Mapped[str | None] = mapped_column(Text(), nullable=True)
    generated_script: Mapped[str | None] = mapped_column(Text(), nullable=True)
    generated_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    generated_tags: Mapped[list[str]] = mapped_column(JSON(), default=list)
    thumbnail_prompt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    production_plan: Mapped[str | None] = mapped_column(Text(), nullable=True)
    visibility: Mapped[VideoVisibility] = mapped_column(
        Enum(VideoVisibility),
        default=VideoVisibility.PRIVATE,
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus),
        default=ReviewStatus.PENDING,
    )
    youtube_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduled_publish_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    idea: Mapped[VideoIdeaModel] = relationship(back_populates="project")
    media_assets: Mapped[list[MediaAssetModel]] = relationship(back_populates="project")
    jobs: Mapped[list[PipelineJobModel]] = relationship(back_populates="project")
    workflow_runs: Mapped[list[WorkflowRunModel]] = relationship(back_populates="project")
    publication_reviews: Mapped[list[PublicationReviewModel]] = relationship(
        back_populates="project"
    )
    analytics_snapshots: Mapped[list[AnalyticsSnapshotModel]] = relationship(
        back_populates="project"
    )
    project_events: Mapped[list[ProjectEventModel]] = relationship(back_populates="project")


class MediaAssetModel(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(100))
    source_adapter: Mapped[str] = mapped_column(String(100))
    source_reference: Mapped[str] = mapped_column(String(500))
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[MediaAssetStatus] = mapped_column(
        Enum(MediaAssetStatus),
        default=MediaAssetStatus.PENDING,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[VideoProjectModel] = relationship(back_populates="media_assets")


class PipelineJobModel(Base):
    __tablename__ = "pipeline_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(100))
    queue_name: Mapped[str] = mapped_column(String(100), default="default")
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[VideoProjectModel] = relationship(back_populates="jobs")


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"), index=True)
    workflow_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    input_payload: Mapped[dict[str, object]] = mapped_column(JSON(), default=dict)
    output_payload: Mapped[dict[str, object]] = mapped_column(JSON(), default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[VideoProjectModel] = relationship(back_populates="workflow_runs")


class PublicationReviewModel(Base):
    __tablename__ = "publication_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"), index=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus),
        default=ReviewStatus.PENDING,
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[VideoProjectModel] = relationship(back_populates="publication_reviews")


class AnalyticsSnapshotModel(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"), index=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    view_count: Mapped[int] = mapped_column(Integer(), default=0)
    like_count: Mapped[int] = mapped_column(Integer(), default=0)
    comment_count: Mapped[int] = mapped_column(Integer(), default=0)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[VideoProjectModel] = relationship(back_populates="analytics_snapshots")


class ProjectEventModel(Base):
    __tablename__ = "project_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=default_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    message: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[VideoProjectModel] = relationship(back_populates="project_events")
