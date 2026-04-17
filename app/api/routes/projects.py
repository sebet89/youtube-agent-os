from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_project_creation_service
from app.services.projects import ProjectCreationService

router = APIRouter(prefix="/projects")


class CreateProjectRequest(BaseModel):
    connection_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)
    raw_idea: str = Field(min_length=1)
    target_audience: str | None = Field(default=None, max_length=255)
    business_goal: str | None = Field(default=None, max_length=255)


@router.post("")
def create_project(
    request: Request,
    payload: CreateProjectRequest,
    service: Annotated[ProjectCreationService, Depends(get_project_creation_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = service.create_project(
            session,
            connection_id=payload.connection_id,
            title=payload.title,
            raw_idea=payload.raw_idea,
            target_audience=payload.target_audience,
            business_goal=payload.business_goal,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    review_url = str(request.url_for("get_project_review_dashboard", project_id=result.project_id))
    return {
        "project_id": result.project_id,
        "idea_id": result.idea_id,
        "connection_id": result.connection_id,
        "youtube_channel_id": result.youtube_channel_id,
        "channel_title": result.channel_title,
        "title": result.title,
        "raw_idea": result.raw_idea,
        "idea_status": result.idea_status,
        "visibility": result.visibility,
        "review_status": result.review_status,
        "review_url": review_url,
    }
