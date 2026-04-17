from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_video_rendering_service
from app.services.rendering import VideoRenderingService

router = APIRouter(prefix="/projects")


@router.post("/{project_id}/render")
def render_project_video(
    project_id: str,
    rendering_service: Annotated[VideoRenderingService, Depends(get_video_rendering_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        result = rendering_service.render_project(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "output_path": result.output_path,
        "asset_count": result.asset_count,
        "idea_status": result.idea_status,
    }
