from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="youtube-agent-os", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    database_url: str = Field(
        default="sqlite+pysqlite:///:memory:",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    youtube_oauth_client_id: str = Field(default="", alias="YOUTUBE_OAUTH_CLIENT_ID")
    youtube_oauth_client_secret: str = Field(default="", alias="YOUTUBE_OAUTH_CLIENT_SECRET")
    youtube_oauth_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/oauth/youtube/callback",
        alias="YOUTUBE_OAUTH_REDIRECT_URI",
    )
    youtube_oauth_scopes_raw: str = Field(
        default="https://www.googleapis.com/auth/youtube.upload,"
        "https://www.googleapis.com/auth/youtube.readonly",
        alias="YOUTUBE_OAUTH_SCOPES",
    )
    youtube_oauth_state_ttl_seconds: int = Field(
        default=600,
        alias="YOUTUBE_OAUTH_STATE_TTL_SECONDS",
    )
    youtube_default_privacy_status: str = Field(
        default="private",
        alias="YOUTUBE_DEFAULT_PRIVACY_STATUS",
    )
    agno_model_id: str | None = Field(default=None, alias="AGNO_MODEL_ID")
    media_output_root: str = Field(
        default="/tmp/youtube-agent-os/assets",
        alias="MEDIA_OUTPUT_ROOT",
    )
    render_output_root: str = Field(
        default="/tmp/youtube-agent-os/renders",
        alias="RENDER_OUTPUT_ROOT",
    )
    ffmpeg_binary: str = Field(default="ffmpeg", alias="FFMPEG_BINARY")
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="us-central1", alias="GOOGLE_CLOUD_LOCATION")
    thumbnail_provider: str = Field(default="deterministic", alias="THUMBNAIL_PROVIDER")
    video_provider: str = Field(default="ffmpeg", alias="VIDEO_PROVIDER")
    vertex_imagen_model: str = Field(
        default="imagen-4.0-fast-generate-001",
        alias="VERTEX_IMAGEN_MODEL",
    )
    vertex_veo_model: str = Field(
        default="veo-3.0-fast-generate-001",
        alias="VERTEX_VEO_MODEL",
    )
    vertex_veo_aspect_ratio: str = Field(default="16:9", alias="VERTEX_VEO_ASPECT_RATIO")
    vertex_veo_resolution: str = Field(default="720p", alias="VERTEX_VEO_RESOLUTION")
    vertex_veo_duration_seconds: int = Field(default=8, alias="VERTEX_VEO_DURATION_SECONDS")
    vertex_veo_generate_audio: bool = Field(default=True, alias="VERTEX_VEO_GENERATE_AUDIO")
    tts_provider: str = Field(default="auto", alias="TTS_PROVIDER")
    tts_voice_name: str | None = Field(default=None, alias="TTS_VOICE_NAME")
    tts_rate: int = Field(default=0, alias="TTS_RATE")
    google_tts_voice_name: str = Field(
        default="pt-BR-Chirp3-HD-Achernar",
        alias="GOOGLE_TTS_VOICE_NAME",
    )
    google_tts_language_code: str = Field(
        default="pt-BR",
        alias="GOOGLE_TTS_LANGUAGE_CODE",
    )
    google_tts_speaking_rate: float = Field(
        default=1.0,
        alias="GOOGLE_TTS_SPEAKING_RATE",
    )
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def youtube_oauth_scopes(self) -> list[str]:
        return [
            scope.strip()
            for scope in self.youtube_oauth_scopes_raw.split(",")
            if scope.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
