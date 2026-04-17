from __future__ import annotations

import base64
import shutil
from collections.abc import Mapping
from pathlib import Path

from app.adapters.google_cloud_media import (
    GoogleCloudMediaSettings,
    GoogleCloudTTSNarrationProvider,
    VertexAIImagenThumbnailGenerator,
    VertexAIVeoVideoRenderer,
)
from app.adapters.rendering import RenderInput


class FakeTokenProvider:
    def get_access_token(self) -> str:
        return "fake-token"


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class FakeHttpClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, Mapping[str, object]]] = []

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: Mapping[str, object],
    ) -> FakeResponse:
        self.requests.append((url, json))
        return FakeResponse(self._responses.pop(0))


def _build_settings() -> GoogleCloudMediaSettings:
    return GoogleCloudMediaSettings(
        project_id="project-123",
        location="us-central1",
        imagen_model="imagen-test",
        veo_model="veo-test",
        veo_aspect_ratio="16:9",
        veo_resolution="720p",
        veo_duration_seconds=8,
        veo_generate_audio=True,
        tts_voice_name="pt-BR-Teste",
        tts_language_code="pt-BR",
        tts_speaking_rate=1.0,
    )


def _fresh_output_dir(name: str) -> Path:
    output_dir = Path.cwd() / name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def test_vertex_imagen_thumbnail_generator_saves_png_variants() -> None:
    output_dir = _fresh_output_dir(".tmp-vertex-imagen")
    image_payload = base64.b64encode(b"fake-image-bytes").decode()
    client = FakeHttpClient(
        responses=[
            {"predictions": [{"bytesBase64Encoded": image_payload}]},
            {"predictions": [{"bytesBase64Encoded": image_payload}]},
            {"predictions": [{"bytesBase64Encoded": image_payload}]},
        ]
    )
    generator = VertexAIImagenThumbnailGenerator(
        settings=_build_settings(),
        token_provider=FakeTokenProvider(),
        http_client=client,
    )

    assets = generator.generate_variants(
        base_path=output_dir,
        slug="video-x",
        title="Titulo de Teste",
        prompt="Prompt visual",
    )

    assert len(assets) == 3
    assert all(Path(asset.storage_path).suffix == ".png" for asset in assets)
    assert all(Path(asset.storage_path).exists() for asset in assets)
    assert assets[0].metadata_json["selected"] is True


def test_vertex_veo_renderer_decodes_inline_video_bytes() -> None:
    output_dir = _fresh_output_dir(".tmp-vertex-veo")
    video_payload = base64.b64encode(b"fake-mp4-bytes").decode()
    client = FakeHttpClient(
        responses=[
            {"name": "operations/veo-123"},
            {"done": True, "response": {"videos": [{"bytesBase64Encoded": video_payload}]}},
        ]
    )
    renderer = VertexAIVeoVideoRenderer(
        settings=_build_settings(),
        token_provider=FakeTokenProvider(),
        http_client=client,
        poll_interval_seconds=0.0,
        max_wait_seconds=1.0,
    )

    result = renderer.render(
        RenderInput(
            project_id="project-1",
            title="Titulo",
            script="Cena um. Cena dois.",
            asset_paths=[],
            output_dir=str(output_dir),
        )
    )

    assert Path(result.output_path).exists()
    assert Path(result.output_path).read_bytes() == b"fake-mp4-bytes"
    assert result.metadata_json["renderer"] == "vertex-veo"
    assert result.metadata_json["theme_name"] == "vertex-veo"


def test_google_cloud_tts_provider_saves_mp3() -> None:
    output_dir = _fresh_output_dir(".tmp-google-tts")
    audio_payload = base64.b64encode(b"fake-mp3-bytes").decode()
    client = FakeHttpClient(responses=[{"audioContent": audio_payload}])
    provider = GoogleCloudTTSNarrationProvider(
        settings=_build_settings(),
        token_provider=FakeTokenProvider(),
        http_client=client,
    )

    result = provider.synthesize(
        payload=type(
            "Payload",
            (),
            {
                "project_id": "project-1",
                "title": "Titulo",
                "script": "Primeira frase. Segunda frase.",
                "output_path": str(output_dir / "voice.wav"),
                "language": "pt-BR",
            },
        )()
    )

    assert Path(result.output_path).suffix == ".mp3"
    assert Path(result.output_path).read_bytes() == b"fake-mp3-bytes"
    assert result.provider == "google-cloud-tts"
