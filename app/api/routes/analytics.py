from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_youtube_analytics_service
from app.services.analytics import YoutubeAnalyticsService

router = APIRouter(prefix="/projects")


@router.post("/{project_id}/analytics/collect")
def collect_project_analytics(
    project_id: str,
    analytics_service: Annotated[
        YoutubeAnalyticsService, Depends(get_youtube_analytics_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str | int]:
    try:
        result = analytics_service.collect_project_analytics(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": result.project_id,
        "youtube_video_id": result.youtube_video_id,
        "view_count": result.view_count,
        "like_count": result.like_count,
        "comment_count": result.comment_count,
        "collected_at": result.collected_at.isoformat(),
    }


@router.get("/{project_id}/analytics")
def list_project_analytics(
    project_id: str,
    analytics_service: Annotated[
        YoutubeAnalyticsService, Depends(get_youtube_analytics_service)
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        snapshots = analytics_service.list_project_analytics(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "project_id": project_id,
        "snapshots": [
            {
                "youtube_video_id": snapshot.youtube_video_id,
                "view_count": snapshot.view_count,
                "like_count": snapshot.like_count,
                "comment_count": snapshot.comment_count,
                "collected_at": snapshot.collected_at.isoformat(),
            }
            for snapshot in snapshots
        ],
    }
