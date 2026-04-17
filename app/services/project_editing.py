from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.repositories import VideoProjectRepository


@dataclass(slots=True)
class ProjectMetadataUpdateResult:
    project_id: str
    generated_title: str | None
    generated_description: str | None
    generated_tags: list[str]
    thumbnail_prompt: str | None


class ProjectEditingService:
    def update_metadata(
        self,
        session: Session,
        *,
        project_id: str,
        generated_title: str | None,
        generated_description: str | None,
        generated_tags: list[str],
        thumbnail_prompt: str | None,
    ) -> ProjectMetadataUpdateResult:
        project = VideoProjectRepository(session).get_project_or_raise(project_id)
        project.generated_title = self._normalize_optional_text(generated_title)
        project.generated_description = self._normalize_optional_text(generated_description)
        project.generated_tags = self._normalize_tags(generated_tags)
        project.thumbnail_prompt = self._normalize_optional_text(thumbnail_prompt)
        session.commit()
        session.refresh(project)

        return ProjectMetadataUpdateResult(
            project_id=project.id,
            generated_title=project.generated_title,
            generated_description=project.generated_description,
            generated_tags=list(project.generated_tags),
            thumbnail_prompt=project.thumbnail_prompt,
        )

    def select_thumbnail_variant(
        self,
        session: Session,
        *,
        project_id: str,
        asset_id: str,
    ) -> str:
        project = VideoProjectRepository(session).get_project_or_raise(project_id)
        thumbnail_assets = [
            asset for asset in project.media_assets if asset.asset_type == "thumbnail"
        ]
        selected_asset = next((asset for asset in thumbnail_assets if asset.id == asset_id), None)
        if selected_asset is None:
            raise ValueError("Thumbnail variant was not found for this project.")

        for asset in thumbnail_assets:
            asset.metadata_json = {
                **asset.metadata_json,
                "selected": asset.id == asset_id,
            }
        session.commit()
        session.refresh(selected_asset)
        return selected_asset.id

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_tags(values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            tag = value.strip()
            if not tag:
                continue
            lowered = tag.casefold()
            if lowered in seen:
                continue
            normalized.append(tag)
            seen.add(lowered)
        return normalized
