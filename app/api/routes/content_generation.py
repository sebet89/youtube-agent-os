from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_content_generation_service, get_db_session
from app.services.content_generation import ContentGenerationService

router = APIRouter(prefix="/projects")


@router.post("/{project_id}/content/generate")
def generate_project_content(
    project_id: str,
    generation_service: Annotated[
        ContentGenerationService, Depends(get_content_generation_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = generation_service.generate_for_project(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "workflow_name": result.workflow_name,
        "team_name": result.team_name,
        "generated_title": result.title,
        "idea_status": result.idea_status,
    }
