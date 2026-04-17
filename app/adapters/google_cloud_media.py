from __future__ import annotations

import base64
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import google.auth
import httpx
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport.requests import Request

from app.adapters.media import PreparedMediaAsset
from app.adapters.narration import NarrationProvider, NarrationRequest, NarrationResult
from app.adapters.rendering import RenderInput, RenderResult, VideoRenderer


class AccessTokenProvider(Protocol):
    def get_access_token(self) -> str:
        """Return a Google Cloud access token."""


class JsonHttpClient(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: Mapping[str, object],
    ) -> Any:
        """Send a JSON HTTP POST request."""


class GoogleADCAccessTokenProvider(AccessTokenProvider):
    def __init__(self) -> None:
        self._request = Request()
        self._credentials: Any | None = None

    def _get_credentials(self) -> Any:
        if self._credentials is None:
            try:
                credentials, _project = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            except google_auth_exceptions.DefaultCredentialsError as exc:
                raise ValueError(
                    "Google Cloud ADC credentials were not found. Configure ADC or use another "
                    "provider."
                ) from exc
            self._credentials = credentials
        return self._credentials

    def get_access_token(self) -> str:
        credentials = self._get_credentials()
        credentials.refresh(self._request)
        token = credentials.token
        if not token:
            raise ValueError("Google Cloud credentials did not return an access token.")
        return str(token)


@dataclass(frozen=True, slots=True)
class GoogleCloudMediaSettings:
    project_id: str
    location: str
    imagen_model: str
    veo_model: str
    veo_aspect_ratio: str
    veo_resolution: str
    veo_duration_seconds: int
    veo_generate_audio: bool
    tts_voice_name: str
    tts_language_code: str
    tts_speaking_rate: float


class VertexAIImagenThumbnailGenerator:
    def __init__(
        self,
        *,
        settings: GoogleCloudMediaSettings,
        token_provider: AccessTokenProvider | None = None,
        http_client: JsonHttpClient | None = None,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider or GoogleADCAccessTokenProvider()
        self._http_client = http_client or httpx.Client(timeout=120.0)

    def generate_variants(
        self,
        *,
        base_path: Path,
        slug: str,
        title: str,
        prompt: str,
    ) -> list[PreparedMediaAsset]:
        variants = [
            (
                "hero",
                "Hero forte com CTA",
                "cinematic YouTube launch frame, bold presenter close-up",
            ),
            (
                "contrast",
                "Contraste alto e energia",
                "high contrast tech teaser, strong motion, dramatic light",
            ),
            (
                "minimal",
                "Minimalista e editorial",
                "editorial premium frame, clean composition, subtle motion cues",
            ),
        ]
        assets: list[PreparedMediaAsset] = []
        for index, (variant_name, label, style_hint) in enumerate(variants):
            image_bytes, used_prompt = self._generate_image_bytes(
                prompt=_compose_imagen_prompt(
                    title=title,
                    prompt=prompt,
                    style_hint=style_hint,
                )
            )
            thumbnail_path = base_path / f"{slug}-thumbnail-{variant_name}.png"
            thumbnail_path.write_bytes(image_bytes)
            assets.append(
                PreparedMediaAsset(
                    asset_type="thumbnail",
                    source_adapter="vertex-imagen",
                    source_reference=used_prompt,
                    storage_path=str(thumbnail_path),
                    metadata_json={
                        "prompt": used_prompt,
                        "format": "png",
                        "variant": variant_name,
                        "label": label,
                        "selected": index == 0,
                        "generator": "vertex-imagen",
                    },
                )
            )
        return assets

    def _generate_image_bytes(self, *, prompt: str) -> tuple[bytes, str]:
        url = (
            f"https://{self._settings.location}-aiplatform.googleapis.com/v1/projects/"
            f"{self._settings.project_id}/locations/{self._settings.location}/publishers/google/"
            f"models/{self._settings.imagen_model}:predict"
        )
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "outputOptions": {"mimeType": "image/png"},
            },
        }
        response = self._http_client.post(
            url,
            headers=_build_google_headers(self._token_provider),
            json=payload,
        )
        response.raise_for_status()
        data = cast(dict[str, object], response.json())
        predictions = data.get("predictions", [])
        if not predictions:
            raise ValueError("Vertex Imagen returned no predictions.")
        if not isinstance(predictions, list):
            raise ValueError("Vertex Imagen returned an invalid predictions payload.")
        first_prediction = predictions[0]
        if not isinstance(first_prediction, dict):
            raise ValueError("Vertex Imagen returned an invalid prediction entry.")
        encoded_image = first_prediction.get("bytesBase64Encoded")
        if not isinstance(encoded_image, str):
            raise ValueError("Vertex Imagen did not return image bytes.")
        used_prompt = str(first_prediction.get("prompt") or prompt)
        return base64.b64decode(encoded_image), used_prompt


class VertexAIVeoVideoRenderer(VideoRenderer):
    def __init__(
        self,
        *,
        settings: GoogleCloudMediaSettings,
        token_provider: AccessTokenProvider | None = None,
        http_client: JsonHttpClient | None = None,
        poll_interval_seconds: float = 8.0,
        max_wait_seconds: float = 900.0,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider or GoogleADCAccessTokenProvider()
        self._http_client = http_client or httpx.Client(timeout=120.0)
        self._poll_interval_seconds = poll_interval_seconds
        self._max_wait_seconds = max_wait_seconds

    def render(self, payload: RenderInput) -> RenderResult:
        output_dir = Path(payload.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{payload.project_id}-final.mp4"
        operation_name = self._start_generation(payload)
        operation_result = self._wait_for_operation(operation_name)
        video_bytes = self._extract_video_bytes(operation_result)
        output_path.write_bytes(video_bytes)
        return RenderResult(
            output_path=str(output_path),
            command=["vertex-veo"],
            metadata_json={
                "renderer": "vertex-veo",
                "model": self._settings.veo_model,
                "asset_count": len(payload.asset_paths),
                "audio_embedded": self._settings.veo_generate_audio,
                "background_music_embedded": False,
                "timeline_sections": ["AI GENERATED VIDEO"],
                "theme_name": "vertex-veo",
                "operation_name": operation_name,
            },
        )

    def _start_generation(self, payload: RenderInput) -> str:
        url = (
            f"https://{self._settings.location}-aiplatform.googleapis.com/v1/projects/"
            f"{self._settings.project_id}/locations/{self._settings.location}/publishers/google/"
            f"models/{self._settings.veo_model}:predictLongRunning"
        )
        instance: dict[str, object] = {
            "prompt": _build_veo_prompt(title=payload.title, script=payload.script),
        }
        reference_image = _find_reference_image(payload.asset_paths)
        if reference_image is not None:
            instance["image"] = {
                "bytesBase64Encoded": base64.b64encode(reference_image.read_bytes()).decode(),
                "mimeType": _guess_mime_type(reference_image),
            }
        response = self._http_client.post(
            url,
            headers=_build_google_headers(self._token_provider),
            json={
                "instances": [instance],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": self._settings.veo_aspect_ratio,
                    "resolution": self._settings.veo_resolution,
                    "durationSeconds": self._settings.veo_duration_seconds,
                    "generateAudio": self._settings.veo_generate_audio,
                    "negativePrompt": (
                        "static slides, text overlays, subtitles burned into frame, "
                        "presentation deck look, low motion, deformed hands"
                    ),
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        operation_name = data.get("name")
        if not isinstance(operation_name, str):
            raise ValueError("Vertex Veo did not return an operation name.")
        return operation_name

    def _wait_for_operation(self, operation_name: str) -> dict[str, object]:
        url = (
            f"https://{self._settings.location}-aiplatform.googleapis.com/v1/projects/"
            f"{self._settings.project_id}/locations/{self._settings.location}/publishers/google/"
            f"models/{self._settings.veo_model}:fetchPredictOperation"
        )
        started_at = time.monotonic()
        while True:
            response = self._http_client.post(
                url,
                headers=_build_google_headers(self._token_provider),
                json={"operationName": operation_name},
            )
            response.raise_for_status()
            data = cast(dict[str, object], response.json())
            if data.get("done") is True:
                return data
            if (time.monotonic() - started_at) > self._max_wait_seconds:
                raise ValueError("Vertex Veo generation timed out.")
            time.sleep(self._poll_interval_seconds)

    @staticmethod
    def _extract_video_bytes(operation_result: dict[str, object]) -> bytes:
        response = operation_result.get("response", {})
        if not isinstance(response, dict):
            raise ValueError("Vertex Veo returned an invalid response payload.")
        videos = response.get("videos", [])
        if not isinstance(videos, list) or not videos:
            raise ValueError("Vertex Veo returned no videos.")
        first_video = videos[0]
        if not isinstance(first_video, dict):
            raise ValueError("Vertex Veo returned an invalid video entry.")
        encoded_video = first_video.get("bytesBase64Encoded")
        if not isinstance(encoded_video, str):
            gcs_uri = first_video.get("gcsUri")
            raise ValueError(
                f"Vertex Veo returned a Cloud Storage URI instead of inline bytes: {gcs_uri}"
            )
        return base64.b64decode(encoded_video)


class GoogleCloudTTSNarrationProvider(NarrationProvider):
    def __init__(
        self,
        *,
        settings: GoogleCloudMediaSettings,
        token_provider: AccessTokenProvider | None = None,
        http_client: JsonHttpClient | None = None,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider or GoogleADCAccessTokenProvider()
        self._http_client = http_client or httpx.Client(timeout=120.0)

    def synthesize(self, payload: NarrationRequest) -> NarrationResult:
        output_path = Path(payload.output_path).with_suffix(".mp3")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response = self._http_client.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            headers=_build_google_headers(self._token_provider),
            json={
                "input": {"ssml": _build_google_tts_ssml(payload.script)},
                "voice": {
                    "languageCode": self._settings.tts_language_code,
                    "name": self._settings.tts_voice_name,
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": self._settings.tts_speaking_rate,
                },
            },
        )
        response.raise_for_status()
        data = cast(dict[str, object], response.json())
        audio_content = data.get("audioContent")
        if not isinstance(audio_content, str):
            raise ValueError("Google Cloud TTS did not return audio content.")
        output_path.write_bytes(base64.b64decode(audio_content))
        return NarrationResult(
            output_path=str(output_path),
            provider="google-cloud-tts",
            duration_seconds=max(2.0, round(len(payload.script.split()) * 0.42, 2)),
            metadata_json={
                "language": self._settings.tts_language_code,
                "voice_name": self._settings.tts_voice_name,
                "format": "mp3",
                "provider_family": "google-cloud-tts",
            },
        )


def _build_google_headers(token_provider: AccessTokenProvider) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token_provider.get_access_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _compose_imagen_prompt(*, title: str, prompt: str, style_hint: str) -> str:
    return (
        f"YouTube thumbnail, 16:9, highly polished creator-brand visual. Title concept: {title}. "
        f"Core idea: {prompt}. Style: {style_hint}. No text baked into image. "
        "Strong subject separation, cinematic lighting, modern color grading."
    )


def _build_veo_prompt(*, title: str, script: str) -> str:
    condensed_script = " ".join(
        segment.strip() for segment in script.splitlines() if segment.strip()
    )
    return (
        "Create a modern short-form cinematic YouTube launch video with natural camera motion, "
        "realistic lighting, believable human presence, and contemporary social-video pacing. "
        f"Project title: {title}. Narrative beats: {condensed_script}. "
        "Avoid slide-show presentation aesthetics, avoid text overlays, and focus on dynamic "
        "scenes."
    )


def _build_google_tts_ssml(script: str) -> str:
    segments = [
        segment.strip()
        for segment in script.replace("\n", " ").split(".")
        if segment.strip()
    ]
    body = "".join(f"<s>{_escape_xml(segment)}</s><break time='350ms'/>" for segment in segments)
    return (
        "<speak>"
        "<prosody rate='medium' pitch='+1st'>"
        f"{body}"
        "</prosody>"
        "</speak>"
    )


def _find_reference_image(asset_paths: list[str]) -> Path | None:
    for asset_path in asset_paths:
        candidate = Path(asset_path)
        if candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and candidate.is_file():
            return candidate
    return None


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
