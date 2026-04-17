from __future__ import annotations

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import Settings
from app.services.interfaces import YoutubeAuthProvider, YoutubeOAuthConnection


class GoogleYoutubeOAuthAdapter(YoutubeAuthProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_authorization_url(self, state: str, code_verifier: str) -> str:
        flow = self._build_flow(state=state)
        flow.code_verifier = code_verifier
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return str(authorization_url)

    def exchange_code_for_connection(
        self,
        code: str,
        code_verifier: str,
    ) -> YoutubeOAuthConnection:
        flow = self._build_flow()
        flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        credentials = flow.credentials
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        response = youtube.channels().list(part="snippet", mine=True).execute()
        items = response.get("items", [])
        if not items:
            raise ValueError("No YouTube channel was returned for the authenticated account.")

        channel = items[0]
        return YoutubeOAuthConnection(
            youtube_channel_id=str(channel["id"]),
            channel_title=str(channel["snippet"]["title"]),
            oauth_subject=str(channel["id"]),
            access_token=str(credentials.token),
            refresh_token=credentials.refresh_token,
            token_expires_at=credentials.expiry,
            scopes=list(credentials.scopes or self._settings.youtube_oauth_scopes),
        )

    def _build_flow(self, state: str | None = None) -> Flow:
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": self._settings.youtube_oauth_client_id,
                    "client_secret": self._settings.youtube_oauth_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self._settings.youtube_oauth_scopes,
            state=state,
        )
        flow.redirect_uri = self._settings.youtube_oauth_redirect_uri
        return flow
