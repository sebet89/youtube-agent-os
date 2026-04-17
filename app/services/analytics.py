from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import TokenCipher
from app.db.models import AnalyticsSnapshotModel, YoutubeChannelConnectionModel
from app.db.repositories import ProjectEventRepository, VideoProjectRepository
from app.services.interfaces import (
    YoutubeAnalyticsProvider,
    YoutubePublishContext,
)


@dataclass(slots=True)
class AnalyticsSnapshotResult:
    project_id: str
    youtube_video_id: str
    view_count: int
    like_count: int
    comment_count: int
    collected_at: datetime


class YoutubeAnalyticsService:
    def __init__(
        self,
        provider: YoutubeAnalyticsProvider,
        token_cipher: TokenCipher,
    ) -> None:
        self._provider = provider
        self._token_cipher = token_cipher

    def collect_project_analytics(
        self,
        session: Session,
        *,
        project_id: str,
    ) -> AnalyticsSnapshotResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)
        connection = repository.get_channel_connection_for_project(project_id)
        if project.youtube_video_id is None:
            raise ValueError("Project must be uploaded to YouTube before collecting analytics.")

        analytics = self._provider.fetch_video_analytics(
            context=self._build_context(connection),
            external_video_id=project.youtube_video_id,
        )
        snapshot = AnalyticsSnapshotModel(
            project_id=project.id,
            youtube_video_id=project.youtube_video_id,
            view_count=analytics.view_count,
            like_count=analytics.like_count,
            comment_count=analytics.comment_count,
            collected_at=datetime.now(UTC),
        )
        session.add(snapshot)
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="analytics_collected",
            message="Analytics basicos do video foram atualizados.",
            metadata_json={
                "youtube_video_id": project.youtube_video_id,
                "view_count": snapshot.view_count,
                "like_count": snapshot.like_count,
                "comment_count": snapshot.comment_count,
            },
        )
        session.commit()
        session.refresh(snapshot)

        return AnalyticsSnapshotResult(
            project_id=project.id,
            youtube_video_id=project.youtube_video_id,
            view_count=snapshot.view_count,
            like_count=snapshot.like_count,
            comment_count=snapshot.comment_count,
            collected_at=snapshot.collected_at,
        )

    def list_project_analytics(
        self,
        session: Session,
        *,
        project_id: str,
    ) -> list[AnalyticsSnapshotResult]:
        VideoProjectRepository(session).get_project_or_raise(project_id)
        query = (
            select(AnalyticsSnapshotModel)
            .where(AnalyticsSnapshotModel.project_id == project_id)
            .order_by(AnalyticsSnapshotModel.collected_at.desc())
        )
        snapshots = list(session.scalars(query))
        return [
            AnalyticsSnapshotResult(
                project_id=snapshot.project_id,
                youtube_video_id=snapshot.youtube_video_id or "",
                view_count=snapshot.view_count,
                like_count=snapshot.like_count,
                comment_count=snapshot.comment_count,
                collected_at=snapshot.collected_at,
            )
            for snapshot in snapshots
        ]

    def get_latest_project_analytics(
        self,
        session: Session,
        *,
        project_id: str,
    ) -> AnalyticsSnapshotResult | None:
        snapshots = self.list_project_analytics(session, project_id=project_id)
        if not snapshots:
            return None
        return snapshots[0]

    def _build_context(
        self,
        connection: YoutubeChannelConnectionModel,
    ) -> YoutubePublishContext:
        access_token_encrypted = connection.access_token_encrypted
        if access_token_encrypted is None:
            raise ValueError("Connected channel is missing an access token.")
        refresh_token_encrypted = connection.refresh_token_encrypted
        return YoutubePublishContext(
            access_token=self._token_cipher.decrypt(access_token_encrypted),
            refresh_token=(
                self._token_cipher.decrypt(refresh_token_encrypted)
                if refresh_token_encrypted is not None
                else None
            ),
            token_expires_at=connection.token_expires_at,
            scopes=list(connection.scopes),
        )
