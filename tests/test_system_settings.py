from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies import get_system_settings_service
from app.main import app
from app.services.system_settings import SystemSettingsService


def test_system_settings_page_renders(client: TestClient) -> None:
    response = client.get("/api/v1/system/settings")

    assert response.status_code == 200
    assert "Configuracoes do sistema" in response.text
    assert "YOUTUBE_OAUTH_CLIENT_ID" in response.text
    assert "GOOGLE_CLOUD_PROJECT" in response.text


def test_system_settings_page_saves_env_file(
    client: TestClient,
) -> None:
    temp_root = Path("C:/Users/Petes/Desktop/Sistemas/social_agent/.runtime/test-system-settings")
    temp_root.mkdir(parents=True, exist_ok=True)
    env_path = temp_root / ".env.test"
    env_path.write_text("APP_NAME=legacy-name\nDEBUG=false\n", encoding="utf-8")

    def override_system_settings_service() -> SystemSettingsService:
        return SystemSettingsService(env_path=str(env_path))

    app.dependency_overrides[get_system_settings_service] = override_system_settings_service
    try:
        response = client.post(
            "/api/v1/system/settings",
            json={
                "values": {
                    "APP_NAME": "youtube-agent-os-local",
                    "DEBUG": "true",
                    "GOOGLE_CLOUD_PROJECT": "agenteia-493505",
                }
            },
        )
    finally:
        app.dependency_overrides.pop(get_system_settings_service, None)

    assert response.status_code == 200
    file_contents = env_path.read_text(encoding="utf-8")
    assert "APP_NAME=youtube-agent-os-local" in file_contents
    assert "DEBUG=true" in file_contents
    assert "GOOGLE_CLOUD_PROJECT=agenteia-493505" in file_contents
