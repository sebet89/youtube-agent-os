from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_project_editing_service
from app.services.project_editing import ProjectEditingService

router = APIRouter(prefix="/projects")


class UpdateProjectMetadataRequest(BaseModel):
    generated_title: str | None = Field(default=None, max_length=255)
    generated_description: str | None = None
    generated_tags: list[str] = Field(default_factory=list)
    thumbnail_prompt: str | None = None


class SelectThumbnailVariantRequest(BaseModel):
    asset_id: str = Field(min_length=1)


@router.patch("/{project_id}/metadata")
def update_project_metadata(
    project_id: str,
    payload: UpdateProjectMetadataRequest,
    service: Annotated[ProjectEditingService, Depends(get_project_editing_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        result = service.update_metadata(
            session,
            project_id=project_id,
            generated_title=payload.generated_title,
            generated_description=payload.generated_description,
            generated_tags=payload.generated_tags,
            thumbnail_prompt=payload.thumbnail_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "generated_title": result.generated_title,
        "generated_description": result.generated_description,
        "generated_tags": result.generated_tags,
        "thumbnail_prompt": result.thumbnail_prompt,
    }


@router.patch("/{project_id}/thumbnail-selection")
def select_thumbnail_variant(
    project_id: str,
    payload: SelectThumbnailVariantRequest,
    service: Annotated[ProjectEditingService, Depends(get_project_editing_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        selected_asset_id = service.select_thumbnail_variant(
            session,
            project_id=project_id,
            asset_id=payload.asset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "project_id": project_id,
        "selected_thumbnail_asset_id": selected_asset_id,
    }
