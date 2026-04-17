from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_youtube_oauth_service
from app.services.oauth import InvalidStateError, YoutubeOAuthService

router = APIRouter(prefix="/oauth/youtube")


@router.get("/authorize")
def authorize_youtube(
    oauth_service: Annotated[YoutubeOAuthService, Depends(get_youtube_oauth_service)],
) -> dict[str, str]:
    oauth_start = oauth_service.build_authorization_start()
    return {
        "authorization_url": oauth_start.authorization_url,
        "state": oauth_start.state,
    }


@router.get("/callback")
def youtube_callback(
    oauth_service: Annotated[YoutubeOAuthService, Depends(get_youtube_oauth_service)],
    session: Annotated[Session, Depends(get_db_session)],
    state: Annotated[str, Query(...)],
    code: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"YouTube OAuth authorization failed: {error}",
        )
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth callback requires an authorization code.",
        )

    try:
        result = oauth_service.handle_callback(session, state=state, code=code)
    except InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "connection_id": result.connection_id,
        "youtube_channel_id": result.youtube_channel_id,
        "channel_title": result.channel_title,
        "connection_status": result.connection_status,
        "scopes": result.scopes,
        "token_expires_at": (
            result.token_expires_at.isoformat() if result.token_expires_at is not None else None
        ),
    }
