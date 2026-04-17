from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import VideoProjectModel
from app.db.repositories import VideoProjectRepository
from app.services.content_generation import ContentGenerationService
from app.services.media_assets import MediaAssetPreparationService
from app.services.rendering import VideoRenderingService


@dataclass(slots=True)
class ProjectPreparationResult:
    project_id: str
    idea_status: str
    executed_steps: list[str]
    skipped_steps: list[str]
    rendered_video_path: str | None


class ProjectPreparationService:
    def __init__(
        self,
        *,
        content_service: ContentGenerationService,
        media_service: MediaAssetPreparationService,
        render_service: VideoRenderingService,
    ) -> None:
        self._content_service = content_service
        self._media_service = media_service
        self._render_service = render_service

    def prepare_reviewable_video(
        self,
        session: Session,
        *,
        project_id: str,
    ) -> ProjectPreparationResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)
        executed_steps: list[str] = []
        skipped_steps: list[str] = []

        if self._needs_content_generation(project):
            self._content_service.generate_for_project(session, project_id=project_id)
            executed_steps.append("content")
            project = repository.get_project_or_raise(project_id)
        else:
            skipped_steps.append("content")

        if self._needs_media_preparation(project):
            self._media_service.prepare_for_project(session, project_id=project_id)
            executed_steps.append("assets")
            project = repository.get_project_or_raise(project_id)
        else:
            skipped_steps.append("assets")

        if self._needs_render(project):
            self._render_service.render_project(session, project_id=project_id)
            executed_steps.append("render")
            project = repository.get_project_or_raise(project_id)
        else:
            skipped_steps.append("render")

        rendered_video = next(
            (asset for asset in project.media_assets if asset.asset_type == "rendered_video"),
            None,
        )
        return ProjectPreparationResult(
            project_id=project.id,
            idea_status=project.idea.status.value,
            executed_steps=executed_steps,
            skipped_steps=skipped_steps,
            rendered_video_path=rendered_video.storage_path if rendered_video is not None else None,
        )

    @staticmethod
    def _needs_content_generation(project: VideoProjectModel) -> bool:
        return not all(
            [
                project.generated_script,
                project.generated_title,
                project.generated_description,
                project.thumbnail_prompt,
                project.production_plan,
            ]
        )

    @staticmethod
    def _needs_media_preparation(project: VideoProjectModel) -> bool:
        asset_types = {asset.asset_type for asset in project.media_assets}
        required_assets = {
            "thumbnail",
            "voiceover_script",
            "voiceover_audio",
            "subtitles_srt",
            "subtitles_vtt",
            "background_music",
        }
        return not required_assets.issubset(asset_types)

    @staticmethod
    def _needs_render(project: VideoProjectModel) -> bool:
        return not any(asset.asset_type == "rendered_video" for asset in project.media_assets)
