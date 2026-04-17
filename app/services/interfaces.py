from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class YoutubeOAuthConnection:
    youtube_channel_id: str
    channel_title: str
    oauth_subject: str | None
    access_token: str
    refresh_token: str | None
    token_expires_at: datetime | None
    scopes: list[str]


@dataclass(slots=True)
class YoutubePublishContext:
    access_token: str
    refresh_token: str | None
    token_expires_at: datetime | None
    scopes: list[str]


@dataclass(slots=True)
class YoutubeVideoUploadRequest:
    title: str
    description: str
    file_path: str
    tags: list[str]


@dataclass(slots=True)
class YoutubeThumbnailUploadRequest:
    external_video_id: str
    file_path: str


@dataclass(slots=True)
class YoutubeCaptionUploadRequest:
    external_video_id: str
    file_path: str
    language: str
    name: str


@dataclass(slots=True)
class YoutubeVideoAnalytics:
    view_count: int
    like_count: int
    comment_count: int


class YoutubeAuthProvider(Protocol):
    def build_authorization_url(self, state: str, code_verifier: str) -> str:
        """Return the OAuth authorization URL for YouTube."""

    def exchange_code_for_connection(
        self,
        code: str,
        code_verifier: str,
    ) -> YoutubeOAuthConnection:
        """Exchange an OAuth code and return the connected YouTube channel context."""


class YoutubePublisher(Protocol):
    def upload_private_video(
        self,
        context: YoutubePublishContext,
        request: YoutubeVideoUploadRequest,
    ) -> str:
        """Upload a video as private and return the external video ID."""

    def publish_video(self, context: YoutubePublishContext, external_video_id: str) -> None:
        """Publish an already uploaded video after human approval."""

    def upload_thumbnail(
        self,
        context: YoutubePublishContext,
        request: YoutubeThumbnailUploadRequest,
    ) -> None:
        """Upload a thumbnail for an existing YouTube video."""

    def upload_caption(
        self,
        context: YoutubePublishContext,
        request: YoutubeCaptionUploadRequest,
    ) -> None:
        """Upload captions for an existing YouTube video."""


class YoutubeAnalyticsProvider(Protocol):
    def fetch_video_analytics(
        self,
        context: YoutubePublishContext,
        external_video_id: str,
    ) -> YoutubeVideoAnalytics:
        """Fetch basic analytics for an uploaded YouTube video."""


class PublicationScheduler(Protocol):
    def schedule_publication(self, *, project_id: str, publish_at: datetime) -> str:
        """Schedule automatic publication for a future date/time."""

    def cancel_publication(self, *, scheduled_task_id: str) -> None:
        """Cancel a previously scheduled automatic publication."""
