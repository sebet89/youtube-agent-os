from __future__ import annotations

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import Settings
from app.services.interfaces import (
    YoutubeCaptionUploadRequest,
    YoutubePublishContext,
    YoutubePublisher,
    YoutubeThumbnailUploadRequest,
    YoutubeVideoUploadRequest,
)


class GoogleYoutubePublisherAdapter(YoutubePublisher):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def upload_private_video(
        self,
        context: YoutubePublishContext,
        request: YoutubeVideoUploadRequest,
    ) -> str:
        youtube = build(
            "youtube",
            "v3",
            credentials=self._build_credentials(context),
            cache_discovery=False,
        )
        media = MediaFileUpload(request.file_path, resumable=True)
        response = (
            youtube.videos()
            .insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": request.title,
                        "description": request.description,
                        "tags": request.tags,
                    },
                    "status": {"privacyStatus": "private"},
                },
                media_body=media,
            )
            .execute()
        )
        return str(response["id"])

    def publish_video(self, context: YoutubePublishContext, external_video_id: str) -> None:
        youtube = build(
            "youtube",
            "v3",
            credentials=self._build_credentials(context),
            cache_discovery=False,
        )
        (
            youtube.videos()
            .update(
                part="status",
                body={
                    "id": external_video_id,
                    "status": {"privacyStatus": "public"},
                },
            )
            .execute()
        )

    def upload_thumbnail(
        self,
        context: YoutubePublishContext,
        request: YoutubeThumbnailUploadRequest,
    ) -> None:
        youtube = build(
            "youtube",
            "v3",
            credentials=self._build_credentials(context),
            cache_discovery=False,
        )
        media = MediaFileUpload(request.file_path)
        youtube.thumbnails().set(videoId=request.external_video_id, media_body=media).execute()

    def upload_caption(
        self,
        context: YoutubePublishContext,
        request: YoutubeCaptionUploadRequest,
    ) -> None:
        youtube = build(
            "youtube",
            "v3",
            credentials=self._build_credentials(context),
            cache_discovery=False,
        )
        media = MediaFileUpload(request.file_path)
        (
            youtube.captions()
            .insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": request.external_video_id,
                        "language": request.language,
                        "name": request.name,
                        "isDraft": False,
                    }
                },
                media_body=media,
            )
            .execute()
        )

    def _build_credentials(self, context: YoutubePublishContext) -> Credentials:
        return Credentials(
            token=context.access_token,
            refresh_token=context.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.youtube_oauth_client_id,
            client_secret=self._settings.youtube_oauth_client_secret,
            scopes=context.scopes,
            expiry=context.token_expires_at,
        )
