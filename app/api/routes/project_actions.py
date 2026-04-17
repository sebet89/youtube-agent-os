from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_db_session,
    get_project_preparation_service,
)
from app.services.project_actions import ProjectPreparationService

router = APIRouter(prefix="/projects")


@router.post("/{project_id}/prepare-video")
def prepare_project_video(
    project_id: str,
    preparation_service: Annotated[
        ProjectPreparationService, Depends(get_project_preparation_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        result = preparation_service.prepare_reviewable_video(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "idea_status": result.idea_status,
        "executed_steps": result.executed_steps,
        "skipped_steps": result.skipped_steps,
        "rendered_video_path": result.rendered_video_path,
    }
