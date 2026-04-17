from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.rendering import RenderInput, VideoRenderer
from app.db.models import MediaAssetModel, VideoProjectModel
from app.db.repositories import ProjectEventRepository, VideoProjectRepository
from app.domain.enums import MediaAssetStatus, VideoIdeaStatus
from app.services.media_assets import _truncate_source_reference


@dataclass(slots=True)
class RenderVideoResult:
    project_id: str
    output_path: str
    asset_count: int
    idea_status: str


class VideoRenderingService:
    def __init__(self, renderer: VideoRenderer, output_root: str) -> None:
        self._renderer = renderer
        self._output_root = output_root

    def render_project(self, session: Session, *, project_id: str) -> RenderVideoResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)
        self._ensure_project_renderable(project_id, project)

        ready_assets = [
            asset for asset in project.media_assets if asset.status == MediaAssetStatus.READY
        ]
        voiceover_audio_asset = next(
            (asset for asset in ready_assets if asset.asset_type == "voiceover_audio"),
            None,
        )
        background_music_asset = next(
            (asset for asset in ready_assets if asset.asset_type == "background_music"),
            None,
        )
        payload = RenderInput(
            project_id=project.id,
            title=project.generated_title or project.idea.title,
            script=project.generated_script or "",
            asset_paths=[asset.storage_path or "" for asset in ready_assets if asset.storage_path],
            output_dir=str(Path(self._output_root) / project.id),
            audio_path=voiceover_audio_asset.storage_path if voiceover_audio_asset else None,
            audio_duration_seconds=_read_audio_duration_seconds(voiceover_audio_asset),
            background_music_path=(
                background_music_asset.storage_path if background_music_asset else None
            ),
        )

        render_result = self._renderer.render(payload)

        existing_render_asset = next(
            (asset for asset in project.media_assets if asset.asset_type == "rendered_video"),
            None,
        )
        if existing_render_asset is None:
            render_asset = MediaAssetModel(
                project_id=project.id,
                asset_type="rendered_video",
                source_adapter="ffmpeg-renderer",
                source_reference=_truncate_source_reference(
                    project.generated_script or project.idea.raw_idea
                ),
                storage_path=render_result.output_path,
                status=MediaAssetStatus.READY,
                metadata_json=render_result.metadata_json,
            )
            session.add(render_asset)
        else:
            existing_render_asset.storage_path = render_result.output_path
            existing_render_asset.status = MediaAssetStatus.READY
            existing_render_asset.metadata_json = render_result.metadata_json

        project.idea.status = VideoIdeaStatus.RENDERED
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="video_rendered",
            message="Video final renderizado e pronto para revisao.",
            metadata_json={
                "output_path": render_result.output_path,
                "asset_count": len(ready_assets),
            },
        )
        session.commit()
        session.refresh(project)

        return RenderVideoResult(
            project_id=project.id,
            output_path=render_result.output_path,
            asset_count=len(ready_assets),
            idea_status=project.idea.status.value,
        )

    @staticmethod
    def _ensure_project_renderable(project_id: str, project: VideoProjectModel) -> None:
        ready_assets = [
            asset for asset in project.media_assets if asset.status == MediaAssetStatus.READY
        ]
        if not ready_assets:
            raise ValueError(
                f"Project '{project_id}' must have prepared media assets before render."
            )
        if not project.generated_script:
            raise ValueError(f"Project '{project_id}' must have generated content before render.")


def _read_audio_duration_seconds(asset: MediaAssetModel | None) -> float | None:
    if asset is None:
        return None
    duration_value = asset.metadata_json.get("duration_seconds")
    if isinstance(duration_value, (int, float)):
        return float(duration_value)
    return None
