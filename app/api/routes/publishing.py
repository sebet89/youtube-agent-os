from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_youtube_publishing_service
from app.domain.exceptions import HumanReviewRequiredError
from app.services.publishing import YoutubePublishingService

router = APIRouter(prefix="/projects")


class UploadProjectRequest(BaseModel):
    file_path: str = Field(min_length=1)


class ApproveProjectRequest(BaseModel):
    reviewer_name: str = Field(min_length=1)
    notes: str | None = None


class RejectProjectRequest(BaseModel):
    reviewer_name: str = Field(min_length=1)
    notes: str | None = None


class ScheduleProjectRequest(BaseModel):
    publish_at: datetime


@router.post("/{project_id}/youtube/upload")
def upload_project_to_youtube(
    project_id: str,
    payload: UploadProjectRequest,
    publishing_service: Annotated[
        YoutubePublishingService, Depends(get_youtube_publishing_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        result = publishing_service.upload_project_video(
            session,
            project_id=project_id,
            file_path=payload.file_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "youtube_video_id": result.youtube_video_id,
        "visibility": result.visibility,
        "idea_status": result.idea_status,
        "thumbnail_uploaded": result.thumbnail_uploaded,
        "captions_uploaded": result.captions_uploaded,
    }


@router.post("/{project_id}/youtube/schedule")
def schedule_project_publication(
    project_id: str,
    payload: ScheduleProjectRequest,
    publishing_service: Annotated[
        YoutubePublishingService, Depends(get_youtube_publishing_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = publishing_service.schedule_project_publication(
            session,
            project_id=project_id,
            publish_at=payload.publish_at,
        )
    except HumanReviewRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "youtube_video_id": result.youtube_video_id,
        "review_status": result.review_status,
        "scheduled_publish_at": result.scheduled_publish_at.isoformat(),
        "scheduled_task_id": result.scheduled_task_id,
    }


@router.post("/{project_id}/youtube/schedule/cancel")
def cancel_scheduled_project_publication(
    project_id: str,
    publishing_service: Annotated[
        YoutubePublishingService, Depends(get_youtube_publishing_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = publishing_service.cancel_scheduled_publication(
            session,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "youtube_video_id": result.youtube_video_id,
        "review_status": result.review_status,
    }


@router.post("/{project_id}/review/approve")
def approve_project_publication(
    project_id: str,
    payload: ApproveProjectRequest,
    publishing_service: Annotated[
        YoutubePublishingService, Depends(get_youtube_publishing_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = publishing_service.approve_project_publication(
            session,
            project_id=project_id,
            reviewer_name=payload.reviewer_name,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "review_status": result.review_status,
        "reviewer_name": result.reviewer_name,
        "reviewed_at": result.reviewed_at.isoformat(),
    }


@router.post("/{project_id}/review/reject")
def reject_project_publication(
    project_id: str,
    payload: RejectProjectRequest,
    publishing_service: Annotated[
        YoutubePublishingService, Depends(get_youtube_publishing_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = publishing_service.reject_project_publication(
            session,
            project_id=project_id,
            reviewer_name=payload.reviewer_name,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "review_status": result.review_status,
        "reviewer_name": result.reviewer_name,
        "reviewed_at": result.reviewed_at.isoformat(),
    }


@router.post("/{project_id}/youtube/publish")
def publish_project_to_youtube(
    project_id: str,
    publishing_service: Annotated[
        YoutubePublishingService, Depends(get_youtube_publishing_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = publishing_service.publish_project_video(session, project_id=project_id)
    except HumanReviewRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "youtube_video_id": result.youtube_video_id,
        "visibility": result.visibility,
        "review_status": result.review_status,
        "published_at": result.published_at.isoformat(),
    }
