from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import YoutubeChannelConnectionModel


def test_authorize_youtube_returns_authorization_url(client: TestClient) -> None:
    response = client.get("/api/v1/oauth/youtube/authorize")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authorization_url"].startswith("https://accounts.google.com/o/oauth2/auth")
    assert payload["state"]
    assert "cv" not in payload["authorization_url"]
    assert "." in payload["state"]


def test_youtube_callback_persists_connection(client: TestClient, db_session: Session) -> None:
    authorize_response = client.get("/api/v1/oauth/youtube/authorize")
    state = authorize_response.json()["state"]

    callback_response = client.get(
        "/api/v1/oauth/youtube/callback",
        params={"state": state, "code": "good-code"},
    )

    assert callback_response.status_code == 200
    payload = callback_response.json()
    assert payload["youtube_channel_id"] == "UC-test-1"
    assert payload["channel_title"] == "Canal MVP"
    assert payload["connection_status"] == "active"

    persisted_connection = db_session.scalar(
        select(YoutubeChannelConnectionModel).where(
            YoutubeChannelConnectionModel.youtube_channel_id == "UC-test-1"
        )
    )

    assert persisted_connection is not None
    assert persisted_connection.channel_title == "Canal MVP"
    assert persisted_connection.access_token_encrypted != "access-token-123"
    assert persisted_connection.refresh_token_encrypted != "refresh-token-123"
    assert persisted_connection.scopes == [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]


def test_youtube_callback_rejects_invalid_state(client: TestClient) -> None:
    response = client.get(
        "/api/v1/oauth/youtube/callback",
        params={"state": "invalid-state", "code": "good-code"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "OAuth state is malformed."
