from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_media_asset_preparation_service
from app.services.media_assets import MediaAssetPreparationService

router = APIRouter(prefix="/projects")


@router.post("/{project_id}/assets/prepare")
def prepare_project_assets(
    project_id: str,
    preparation_service: Annotated[
        MediaAssetPreparationService, Depends(get_media_asset_preparation_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        result = preparation_service.prepare_for_project(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "asset_count": result.asset_count,
        "asset_types": result.asset_types,
        "idea_status": result.idea_status,
    }
