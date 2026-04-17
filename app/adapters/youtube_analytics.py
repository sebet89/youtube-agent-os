from __future__ import annotations

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings
from app.services.interfaces import (
    YoutubeAnalyticsProvider,
    YoutubePublishContext,
    YoutubeVideoAnalytics,
)


class GoogleYoutubeAnalyticsAdapter(YoutubeAnalyticsProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_video_analytics(
        self,
        context: YoutubePublishContext,
        external_video_id: str,
    ) -> YoutubeVideoAnalytics:
        credentials = Credentials(
            token=context.access_token,
            refresh_token=context.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.youtube_oauth_client_id,
            client_secret=self._settings.youtube_oauth_client_secret,
            scopes=context.scopes,
        )
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        response = (
            youtube.videos()
            .list(part="statistics", id=external_video_id)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            raise ValueError(f"YouTube video '{external_video_id}' was not found.")

        statistics = items[0].get("statistics", {})
        return YoutubeVideoAnalytics(
            view_count=int(statistics.get("viewCount", 0)),
            like_count=int(statistics.get("likeCount", 0)),
            comment_count=int(statistics.get("commentCount", 0)),
        )
