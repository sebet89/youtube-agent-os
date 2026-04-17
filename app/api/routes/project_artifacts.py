from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.db.models import MediaAssetModel
from app.db.repositories import VideoProjectRepository

router = APIRouter(prefix="/projects")


@router.get("/{project_id}/artifacts/rendered-video")
def get_rendered_video_artifact(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> FileResponse:
    return _serve_project_asset_file(
        session=session,
        project_id=project_id,
        asset_type="rendered_video",
        media_type="video/mp4",
        filename="rendered-video.mp4",
    )


@router.get("/{project_id}/artifacts/thumbnail")
def get_thumbnail_artifact(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> FileResponse:
    project = VideoProjectRepository(session).get_project_or_raise(project_id)
    asset = next(
        (
            item
            for item in project.media_assets
            if item.asset_type == "thumbnail" and item.metadata_json.get("selected") is True
        ),
        None,
    )
    if asset is None:
        asset = next(
            (item for item in project.media_assets if item.asset_type == "thumbnail"),
            None,
        )
    return _serve_asset(
        asset=asset,
        asset_type="thumbnail",
        media_type="image/svg+xml",
        filename="thumbnail.svg",
    )


@router.get("/{project_id}/artifacts/thumbnail/{asset_id}")
def get_thumbnail_variant_artifact(
    project_id: str,
    asset_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> FileResponse:
    project = VideoProjectRepository(session).get_project_or_raise(project_id)
    asset = next(
        (
            item
            for item in project.media_assets
            if item.asset_type == "thumbnail" and item.id == asset_id
        ),
        None,
    )
    return _serve_asset(
        asset=asset,
        asset_type="thumbnail",
        media_type="image/svg+xml",
        filename=f"{asset_id}.svg",
    )


def _serve_project_asset_file(
    *,
    session: Session,
    project_id: str,
    asset_type: str,
    media_type: str,
    filename: str,
) -> FileResponse:
    project = VideoProjectRepository(session).get_project_or_raise(project_id)
    asset = next((item for item in project.media_assets if item.asset_type == asset_type), None)
    return _serve_asset(
        asset=asset,
        asset_type=asset_type,
        media_type=media_type,
        filename=filename,
    )


def _serve_asset(
    *,
    asset: MediaAssetModel | None,
    asset_type: str,
    media_type: str,
    filename: str,
) -> FileResponse:
    if asset is None or asset.storage_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_type}' is not available for this project.",
        )

    file_path = Path(asset.storage_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset file for '{asset_type}' was not found on disk.",
        )

    return FileResponse(path=file_path, media_type=media_type, filename=filename)
