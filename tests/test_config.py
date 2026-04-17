from app.core.config import Settings


def test_settings_default_visibility_is_private() -> None:
    settings = Settings()

    assert settings.youtube_default_privacy_status == "private"

