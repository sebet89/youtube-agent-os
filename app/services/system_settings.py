from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class SystemSettingOption:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class SystemSettingFieldDefinition:
    env_key: str
    label: str
    help_text: str
    input_type: str = "text"
    multiline: bool = False
    options: tuple[SystemSettingOption, ...] = ()
    placeholder: str = ""


@dataclass(frozen=True, slots=True)
class SystemSettingSectionDefinition:
    title: str
    description: str
    fields: tuple[SystemSettingFieldDefinition, ...]


@dataclass(frozen=True, slots=True)
class SystemSettingFieldSnapshot:
    env_key: str
    label: str
    help_text: str
    value: str
    input_type: str
    multiline: bool
    options: tuple[SystemSettingOption, ...]
    placeholder: str


@dataclass(frozen=True, slots=True)
class SystemSettingSectionSnapshot:
    title: str
    description: str
    fields: tuple[SystemSettingFieldSnapshot, ...]


@dataclass(frozen=True, slots=True)
class SystemSettingsSnapshot:
    env_path: str
    sections: tuple[SystemSettingSectionSnapshot, ...]


@dataclass(frozen=True, slots=True)
class SavedSystemSettings:
    env_path: str
    updated_keys: tuple[str, ...]


SYSTEM_SETTING_SECTIONS: tuple[SystemSettingSectionDefinition, ...] = (
    SystemSettingSectionDefinition(
        title="Aplicacao",
        description="Controle o comportamento local da API e as rotas base do sistema.",
        fields=(
            SystemSettingFieldDefinition(
                env_key="APP_NAME",
                label="Nome da aplicacao",
                help_text="Titulo apresentado pela API e interfaces server-side.",
            ),
            SystemSettingFieldDefinition(
                env_key="APP_ENV",
                label="Ambiente",
                help_text="Use development para local e production quando endurecer o deploy.",
                options=(
                    SystemSettingOption("development", "development"),
                    SystemSettingOption("production", "production"),
                    SystemSettingOption("test", "test"),
                ),
            ),
            SystemSettingFieldDefinition(
                env_key="DEBUG",
                label="Debug",
                help_text="Liga mensagens de desenvolvimento e respostas mais verbosas.",
                options=(
                    SystemSettingOption("true", "true"),
                    SystemSettingOption("false", "false"),
                ),
            ),
            SystemSettingFieldDefinition(
                env_key="API_PREFIX",
                label="Prefixo da API",
                help_text="Prefixo usado para registrar as rotas FastAPI.",
            ),
            SystemSettingFieldDefinition(
                env_key="SECRET_KEY",
                label="Secret key",
                help_text="Chave usada para assinatura de state OAuth e cifragem local.",
                input_type="password",
            ),
        ),
    ),
    SystemSettingSectionDefinition(
        title="Infraestrutura",
        description="Ajuste conexoes locais de banco, fila e caminhos de trabalho.",
        fields=(
            SystemSettingFieldDefinition(
                env_key="DATABASE_URL",
                label="Database URL",
                help_text="String completa de conexao do SQLAlchemy.",
            ),
            SystemSettingFieldDefinition(
                env_key="REDIS_URL",
                label="Redis URL",
                help_text="Fila e broker do Celery.",
            ),
            SystemSettingFieldDefinition(
                env_key="MEDIA_OUTPUT_ROOT",
                label="Pasta de assets",
                help_text="Diretorio onde thumbnails, audios e legendas sao gravados.",
            ),
            SystemSettingFieldDefinition(
                env_key="RENDER_OUTPUT_ROOT",
                label="Pasta de renders",
                help_text="Diretorio onde os videos finais sao exportados.",
            ),
            SystemSettingFieldDefinition(
                env_key="FFMPEG_BINARY",
                label="Executavel FFmpeg",
                help_text="Nome ou caminho absoluto do binario ffmpeg.",
            ),
        ),
    ),
    SystemSettingSectionDefinition(
        title="YouTube OAuth",
        description="Credenciais e detalhes da integracao oficial com a conta do YouTube.",
        fields=(
            SystemSettingFieldDefinition(
                env_key="YOUTUBE_OAUTH_CLIENT_ID",
                label="Client ID",
                help_text="OAuth Client ID do Google Cloud para o YouTube.",
                input_type="password",
            ),
            SystemSettingFieldDefinition(
                env_key="YOUTUBE_OAUTH_CLIENT_SECRET",
                label="Client Secret",
                help_text="OAuth Client Secret do Google Cloud.",
                input_type="password",
            ),
            SystemSettingFieldDefinition(
                env_key="YOUTUBE_OAUTH_REDIRECT_URI",
                label="Redirect URI",
                help_text="Precisa bater exatamente com o valor cadastrado no Google Cloud.",
            ),
            SystemSettingFieldDefinition(
                env_key="YOUTUBE_OAUTH_SCOPES",
                label="Scopes",
                help_text="Lista separada por virgula com os escopos do YouTube.",
                multiline=True,
            ),
            SystemSettingFieldDefinition(
                env_key="YOUTUBE_DEFAULT_PRIVACY_STATUS",
                label="Privacidade inicial",
                help_text="Privacidade usada no upload inicial para o YouTube.",
                options=(
                    SystemSettingOption("private", "private"),
                    SystemSettingOption("unlisted", "unlisted"),
                    SystemSettingOption("public", "public"),
                ),
            ),
        ),
    ),
    SystemSettingSectionDefinition(
        title="Midia e IA",
        description="Escolha os providers de thumbnail, video e narracao usados pelo pipeline.",
        fields=(
            SystemSettingFieldDefinition(
                env_key="GOOGLE_CLOUD_PROJECT",
                label="Google Cloud Project",
                help_text="Project ID usado para Vertex AI e Google TTS.",
            ),
            SystemSettingFieldDefinition(
                env_key="GOOGLE_CLOUD_LOCATION",
                label="Google Cloud Location",
                help_text="Regiao do Vertex AI, como us-central1.",
            ),
            SystemSettingFieldDefinition(
                env_key="THUMBNAIL_PROVIDER",
                label="Provider de thumbnail",
                help_text="deterministic para local ou vertex_imagen para Vertex AI.",
                options=(
                    SystemSettingOption("deterministic", "deterministic"),
                    SystemSettingOption("vertex_imagen", "vertex_imagen"),
                ),
            ),
            SystemSettingFieldDefinition(
                env_key="VIDEO_PROVIDER",
                label="Provider de video",
                help_text="ffmpeg para local ou vertex_veo para video generativo.",
                options=(
                    SystemSettingOption("ffmpeg", "ffmpeg"),
                    SystemSettingOption("vertex_veo", "vertex_veo"),
                ),
            ),
            SystemSettingFieldDefinition(
                env_key="TTS_PROVIDER",
                label="Provider de voz",
                help_text="auto, edge_tts, windows_speech, synthetic ou google_cloud.",
                options=(
                    SystemSettingOption("auto", "auto"),
                    SystemSettingOption("edge_tts", "edge_tts"),
                    SystemSettingOption("windows_speech", "windows_speech"),
                    SystemSettingOption("synthetic", "synthetic"),
                    SystemSettingOption("google_cloud", "google_cloud"),
                ),
            ),
            SystemSettingFieldDefinition(
                env_key="TTS_VOICE_NAME",
                label="Voice name local",
                help_text="Voz usada por edge-tts ou Windows Speech.",
            ),
            SystemSettingFieldDefinition(
                env_key="TTS_RATE",
                label="Rate local",
                help_text="Velocidade da voz local. Use 0 para neutro.",
                input_type="number",
            ),
            SystemSettingFieldDefinition(
                env_key="VERTEX_IMAGEN_MODEL",
                label="Modelo Imagen",
                help_text="Modelo do Vertex AI para gerar thumbnails.",
            ),
            SystemSettingFieldDefinition(
                env_key="VERTEX_VEO_MODEL",
                label="Modelo Veo",
                help_text="Modelo do Vertex AI para gerar videos.",
            ),
            SystemSettingFieldDefinition(
                env_key="VERTEX_VEO_ASPECT_RATIO",
                label="Aspect ratio Veo",
                help_text="Formato visual do video gerado, como 16:9.",
            ),
            SystemSettingFieldDefinition(
                env_key="VERTEX_VEO_RESOLUTION",
                label="Resolucao Veo",
                help_text="Resolucao alvo, como 720p ou 1080p.",
            ),
            SystemSettingFieldDefinition(
                env_key="VERTEX_VEO_DURATION_SECONDS",
                label="Duracao Veo",
                help_text="Duracao do video em segundos.",
                input_type="number",
            ),
            SystemSettingFieldDefinition(
                env_key="VERTEX_VEO_GENERATE_AUDIO",
                label="Gerar audio no Veo",
                help_text="Habilita audio nativo quando o modelo suportar.",
                options=(
                    SystemSettingOption("true", "true"),
                    SystemSettingOption("false", "false"),
                ),
            ),
            SystemSettingFieldDefinition(
                env_key="GOOGLE_TTS_VOICE_NAME",
                label="Voz Google TTS",
                help_text="Nome completo da voz do Google Cloud TTS.",
            ),
            SystemSettingFieldDefinition(
                env_key="GOOGLE_TTS_LANGUAGE_CODE",
                label="Idioma Google TTS",
                help_text="Codigo do idioma usado na locucao, como pt-BR.",
            ),
            SystemSettingFieldDefinition(
                env_key="GOOGLE_TTS_SPEAKING_RATE",
                label="Velocidade Google TTS",
                help_text="Velocidade da fala no Google TTS.",
                input_type="number",
            ),
        ),
    ),
)


class SystemSettingsService:
    def __init__(
        self,
        *,
        env_path: str = ".env",
        settings_provider: Callable[[], Settings] = get_settings,
    ) -> None:
        self._env_path = Path(env_path)
        self._settings_provider = settings_provider

    def get_snapshot(self) -> SystemSettingsSnapshot:
        current_values = self._load_current_values()
        return SystemSettingsSnapshot(
            env_path=str(self._env_path.resolve()),
            sections=tuple(
                SystemSettingSectionSnapshot(
                    title=section.title,
                    description=section.description,
                    fields=tuple(
                        SystemSettingFieldSnapshot(
                            env_key=field.env_key,
                            label=field.label,
                            help_text=field.help_text,
                            value=current_values.get(field.env_key, ""),
                            input_type=field.input_type,
                            multiline=field.multiline,
                            options=field.options,
                            placeholder=field.placeholder,
                        )
                        for field in section.fields
                    ),
                )
                for section in SYSTEM_SETTING_SECTIONS
            ),
        )

    def save(self, values: dict[str, str]) -> SavedSystemSettings:
        current_values = self._load_current_values()
        managed_keys = self.managed_keys
        for key in managed_keys:
            if key not in values:
                continue
            current_values[key] = self._normalize_value(values[key])

        file_contents = self._render_env_file(current_values)
        self._env_path.write_text(file_contents, encoding="utf-8")
        get_settings.cache_clear()
        return SavedSystemSettings(
            env_path=str(self._env_path.resolve()),
            updated_keys=tuple(key for key in managed_keys if key in values),
        )

    @property
    def managed_keys(self) -> tuple[str, ...]:
        return tuple(
            field.env_key
            for section in SYSTEM_SETTING_SECTIONS
            for field in section.fields
        )

    def _load_current_values(self) -> dict[str, str]:
        settings = self._settings_provider()
        file_values = self._read_env_file()
        default_values = {
            "APP_NAME": settings.app_name,
            "APP_ENV": settings.app_env,
            "DEBUG": _bool_to_env(settings.debug),
            "API_PREFIX": settings.api_prefix,
            "DATABASE_URL": settings.database_url,
            "REDIS_URL": settings.redis_url,
            "YOUTUBE_OAUTH_CLIENT_ID": settings.youtube_oauth_client_id,
            "YOUTUBE_OAUTH_CLIENT_SECRET": settings.youtube_oauth_client_secret,
            "YOUTUBE_OAUTH_REDIRECT_URI": settings.youtube_oauth_redirect_uri,
            "YOUTUBE_OAUTH_SCOPES": settings.youtube_oauth_scopes_raw,
            "YOUTUBE_DEFAULT_PRIVACY_STATUS": settings.youtube_default_privacy_status,
            "MEDIA_OUTPUT_ROOT": settings.media_output_root,
            "RENDER_OUTPUT_ROOT": settings.render_output_root,
            "FFMPEG_BINARY": settings.ffmpeg_binary,
            "GOOGLE_CLOUD_PROJECT": settings.google_cloud_project or "",
            "GOOGLE_CLOUD_LOCATION": settings.google_cloud_location,
            "THUMBNAIL_PROVIDER": settings.thumbnail_provider,
            "VIDEO_PROVIDER": settings.video_provider,
            "TTS_PROVIDER": settings.tts_provider,
            "TTS_VOICE_NAME": settings.tts_voice_name or "",
            "TTS_RATE": str(settings.tts_rate),
            "VERTEX_IMAGEN_MODEL": settings.vertex_imagen_model,
            "VERTEX_VEO_MODEL": settings.vertex_veo_model,
            "VERTEX_VEO_ASPECT_RATIO": settings.vertex_veo_aspect_ratio,
            "VERTEX_VEO_RESOLUTION": settings.vertex_veo_resolution,
            "VERTEX_VEO_DURATION_SECONDS": str(settings.vertex_veo_duration_seconds),
            "VERTEX_VEO_GENERATE_AUDIO": _bool_to_env(settings.vertex_veo_generate_audio),
            "GOOGLE_TTS_VOICE_NAME": settings.google_tts_voice_name,
            "GOOGLE_TTS_LANGUAGE_CODE": settings.google_tts_language_code,
            "GOOGLE_TTS_SPEAKING_RATE": str(settings.google_tts_speaking_rate),
            "SECRET_KEY": settings.secret_key,
        }
        default_values.update(file_values)
        return default_values

    def _read_env_file(self) -> dict[str, str]:
        if not self._env_path.exists():
            return {}
        values: dict[str, str] = {}
        for raw_line in self._env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw_value = raw_line.split("=", 1)
            values[key.strip()] = raw_value.strip()
        return values

    def _render_env_file(self, values: dict[str, str]) -> str:
        lines: list[str] = [
            "# Arquivo gerado pela tela de configuracoes do youtube-agent-os.",
            "# Reinicie a API e o worker se alterar providers, filas ou credenciais.",
            "",
        ]
        for section in SYSTEM_SETTING_SECTIONS:
            lines.append(f"# {section.title}")
            for field in section.fields:
                lines.append(f"{field.env_key}={values.get(field.env_key, '')}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _normalize_value(value: str) -> str:
        return value.strip()


def _bool_to_env(value: bool) -> str:
    return "true" if value else "false"
