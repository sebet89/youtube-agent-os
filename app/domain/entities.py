from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.enums import (
    ChannelConnectionStatus,
    JobStatus,
    MediaAssetStatus,
    ReviewStatus,
    VideoIdeaStatus,
    VideoVisibility,
)
from app.domain.exceptions import HumanReviewRequiredError


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class YoutubeChannelConnection:
    youtube_channel_id: str
    channel_title: str
    connection_status: ChannelConnectionStatus = ChannelConnectionStatus.PENDING
    scopes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class VideoIdea:
    channel_connection_id: str
    title: str
    raw_idea: str
    target_audience: str | None = None
    business_goal: str | None = None
    status: VideoIdeaStatus = VideoIdeaStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class PublicationReview:
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_name: str | None = None
    notes: str | None = None
    reviewed_at: datetime | None = None

    def approve(self, reviewer_name: str, notes: str | None = None) -> None:
        self.status = ReviewStatus.APPROVED
        self.reviewer_name = reviewer_name
        self.notes = notes
        self.reviewed_at = utc_now()

    def reject(self, reviewer_name: str, notes: str | None = None) -> None:
        self.status = ReviewStatus.REJECTED
        self.reviewer_name = reviewer_name
        self.notes = notes
        self.reviewed_at = utc_now()


@dataclass(slots=True)
class VideoProject:
    idea_id: str
    visibility: VideoVisibility = VideoVisibility.PRIVATE
    review_status: ReviewStatus = ReviewStatus.PENDING
    generated_title: str | None = None
    generated_description: str | None = None
    generated_tags: list[str] = field(default_factory=list)
    thumbnail_prompt: str | None = None
    youtube_video_id: str | None = None
    published_at: datetime | None = None

    def can_publish_publicly(self) -> bool:
        return self.review_status == ReviewStatus.APPROVED

    def publish_publicly(self) -> None:
        if not self.can_publish_publicly():
            raise HumanReviewRequiredError(
                "Projects can only move to public visibility after human approval."
            )

        self.visibility = VideoVisibility.PUBLIC
        self.published_at = utc_now()


@dataclass(slots=True)
class MediaAsset:
    project_id: str
    asset_type: str
    source_adapter: str
    source_reference: str
    status: MediaAssetStatus = MediaAssetStatus.PENDING
    storage_path: str | None = None


@dataclass(slots=True)
class PipelineJob:
    project_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    queue_name: str = "default"
    celery_task_id: str | None = None


@dataclass(slots=True)
class WorkflowRun:
    project_id: str
    workflow_name: str
    status: JobStatus = JobStatus.PENDING


@dataclass(slots=True)
class AnalyticsSnapshot:
    project_id: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
