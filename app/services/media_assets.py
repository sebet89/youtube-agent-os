from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.media import MediaAssetAdapter, MediaPreparationInput
from app.db.models import MediaAssetModel, VideoProjectModel
from app.db.repositories import ProjectEventRepository, VideoProjectRepository
from app.domain.enums import MediaAssetStatus, VideoIdeaStatus


@dataclass(slots=True)
class MediaPreparationResult:
    project_id: str
    asset_count: int
    asset_types: list[str]
    idea_status: str


class MediaAssetPreparationService:
    def __init__(self, adapter: MediaAssetAdapter) -> None:
        self._adapter = adapter

    def prepare_for_project(self, session: Session, *, project_id: str) -> MediaPreparationResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)
        self._ensure_project_ready(project_id, project)

        payload = MediaPreparationInput(
            project_id=project.id,
            generated_title=project.generated_title or project.idea.title,
            generated_script=project.generated_script or "",
            thumbnail_prompt=project.thumbnail_prompt or "",
            production_plan=project.production_plan or "",
        )

        existing_assets = list(project.media_assets)
        for asset in existing_assets:
            session.delete(asset)
        session.flush()

        prepared_assets = self._adapter.prepare_assets(payload)
        persisted_assets: list[MediaAssetModel] = []
        for prepared_asset in prepared_assets:
            persisted_assets.append(
                MediaAssetModel(
                    project_id=project.id,
                    asset_type=prepared_asset.asset_type,
                    source_adapter=prepared_asset.source_adapter,
                    source_reference=_truncate_source_reference(prepared_asset.source_reference),
                    storage_path=prepared_asset.storage_path,
                    status=MediaAssetStatus.READY,
                    metadata_json=prepared_asset.metadata_json,
                )
            )

        session.add_all(persisted_assets)
        project.idea.status = VideoIdeaStatus.RENDER_READY
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="media_prepared",
            message="Assets de midia foram preparados para o render.",
            metadata_json={
                "asset_count": len(persisted_assets),
                "asset_types": [asset.asset_type for asset in persisted_assets],
            },
        )
        session.commit()
        session.refresh(project)

        return MediaPreparationResult(
            project_id=project.id,
            asset_count=len(persisted_assets),
            asset_types=[asset.asset_type for asset in persisted_assets],
            idea_status=project.idea.status.value,
        )

    @staticmethod
    def _ensure_project_ready(project_id: str, project: VideoProjectModel) -> None:
        generated_script = project.generated_script
        thumbnail_prompt = project.thumbnail_prompt
        production_plan = project.production_plan
        if not generated_script or not thumbnail_prompt or not production_plan:
            raise ValueError(
                f"Project '{project_id}' must have generated content before media preparation."
            )


def _truncate_source_reference(value: str, *, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."
