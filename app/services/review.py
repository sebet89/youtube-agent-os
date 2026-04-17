from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.repositories import VideoProjectRepository


@dataclass(slots=True)
class ReviewAssetSummary:
    asset_type: str
    status: str
    storage_path: str | None
    source_adapter: str


@dataclass(slots=True)
class ReviewJobSummary:
    job_type: str
    status: str
    queue_name: str
    celery_task_id: str | None


@dataclass(slots=True)
class ReviewThumbnailVariantSummary:
    asset_id: str
    label: str
    storage_path: str | None
    is_selected: bool
    uploaded_to_youtube: bool


@dataclass(slots=True)
class ReviewProjectEventSummary:
    event_type: str
    message: str
    created_at: str


@dataclass(slots=True)
class ReviewDashboardSnapshot:
    project_id: str
    idea_title: str
    raw_idea: str
    idea_status: str
    visibility: str
    review_status: str
    generated_title: str | None
    generated_description: str | None
    generated_tags: list[str]
    generated_script: str | None
    thumbnail_prompt: str | None
    production_plan: str | None
    youtube_video_id: str | None
    rendered_video_path: str | None
    thumbnail_asset_path: str | None
    scheduled_publish_at: datetime | None
    scheduled_publish_task_id: str | None
    latest_view_count: int | None
    latest_like_count: int | None
    latest_comment_count: int | None
    subtitle_preview: str | None
    selected_thumbnail_asset_id: str | None
    thumbnail_variants: list[ReviewThumbnailVariantSummary]
    youtube_thumbnail_uploaded: bool
    youtube_captions_uploaded: bool
    uploaded_caption_language: str | None
    events: list[ReviewProjectEventSummary]
    assets: list[ReviewAssetSummary]
    jobs: list[ReviewJobSummary]


class HumanReviewDashboardService:
    def get_project_snapshot(
        self,
        session: Session,
        *,
        project_id: str,
    ) -> ReviewDashboardSnapshot:
        project = VideoProjectRepository(session).get_project_or_raise(project_id)
        rendered_video = next(
            (asset for asset in project.media_assets if asset.asset_type == "rendered_video"),
            None,
        )
        thumbnail_assets = [
            asset for asset in project.media_assets if asset.asset_type == "thumbnail"
        ]
        thumbnail_asset = next(
            (asset for asset in thumbnail_assets if asset.metadata_json.get("selected") is True),
            thumbnail_assets[0] if thumbnail_assets else None,
        )
        subtitle_preview = self._read_subtitle_preview(
            next(
                (asset for asset in project.media_assets if asset.asset_type == "subtitles_srt"),
                None,
            )
        )
        subtitle_asset = next(
            (asset for asset in project.media_assets if asset.asset_type == "subtitles_srt"),
            None,
        )
        latest_analytics = max(
            project.analytics_snapshots,
            key=lambda snapshot: snapshot.collected_at,
            default=None,
        )

        return ReviewDashboardSnapshot(
            project_id=project.id,
            idea_title=project.idea.title,
            raw_idea=project.idea.raw_idea,
            idea_status=project.idea.status.value,
            visibility=project.visibility.value,
            review_status=project.review_status.value,
            generated_title=project.generated_title,
            generated_description=project.generated_description,
            generated_tags=list(project.generated_tags),
            generated_script=project.generated_script,
            thumbnail_prompt=project.thumbnail_prompt,
            production_plan=project.production_plan,
            youtube_video_id=project.youtube_video_id,
            rendered_video_path=rendered_video.storage_path if rendered_video is not None else None,
            thumbnail_asset_path=(
                thumbnail_asset.storage_path if thumbnail_asset is not None else None
            ),
            scheduled_publish_at=project.scheduled_publish_at,
            scheduled_publish_task_id=project.scheduled_publish_task_id,
            latest_view_count=(
                latest_analytics.view_count if latest_analytics is not None else None
            ),
            latest_like_count=(
                latest_analytics.like_count if latest_analytics is not None else None
            ),
            latest_comment_count=(
                latest_analytics.comment_count if latest_analytics is not None else None
            ),
            subtitle_preview=subtitle_preview,
            selected_thumbnail_asset_id=thumbnail_asset.id if thumbnail_asset is not None else None,
            thumbnail_variants=[
                ReviewThumbnailVariantSummary(
                    asset_id=asset.id,
                    label=str(
                        asset.metadata_json.get("label")
                        or asset.metadata_json.get("variant")
                        or "Thumbnail"
                    ),
                    storage_path=asset.storage_path,
                    is_selected=bool(asset.metadata_json.get("selected")),
                    uploaded_to_youtube=bool(asset.metadata_json.get("uploaded_to_youtube")),
                )
                for asset in thumbnail_assets
            ],
            youtube_thumbnail_uploaded=(
                bool(thumbnail_asset.metadata_json.get("uploaded_to_youtube"))
                if thumbnail_asset is not None
                else False
            ),
            youtube_captions_uploaded=(
                bool(subtitle_asset.metadata_json.get("uploaded_to_youtube"))
                if subtitle_asset is not None
                else False
            ),
            uploaded_caption_language=(
                str(subtitle_asset.metadata_json.get("uploaded_language"))
                if (
                    subtitle_asset is not None
                    and subtitle_asset.metadata_json.get("uploaded_language")
                )
                else None
            ),
            events=[
                ReviewProjectEventSummary(
                    event_type=event.event_type,
                    message=event.message,
                    created_at=event.created_at.isoformat(),
                )
                for event in sorted(
                    project.project_events,
                    key=lambda item: item.created_at,
                    reverse=True,
                )
            ],
            assets=[
                ReviewAssetSummary(
                    asset_type=asset.asset_type,
                    status=asset.status.value,
                    storage_path=asset.storage_path,
                    source_adapter=asset.source_adapter,
                )
                for asset in sorted(project.media_assets, key=lambda item: item.created_at)
            ],
            jobs=[
                ReviewJobSummary(
                    job_type=job.job_type,
                    status=job.status.value,
                    queue_name=job.queue_name,
                    celery_task_id=job.celery_task_id,
                )
                for job in sorted(project.jobs, key=lambda item: item.created_at, reverse=True)
            ],
        )

    @staticmethod
    def _read_subtitle_preview(asset: object) -> str | None:
        storage_path = getattr(asset, "storage_path", None)
        if storage_path is None:
            return None
        file_path = Path(storage_path)
        if not file_path.is_file():
            return None
        return file_path.read_text(encoding="utf-8")[:1800]
