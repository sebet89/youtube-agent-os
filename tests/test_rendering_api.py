from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MediaAssetModel, VideoProjectModel
from app.domain.enums import MediaAssetStatus, VideoIdeaStatus


def test_render_project_creates_final_video_asset(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    assert client.post(f"/api/v1/projects/{sample_project_id}/content/generate").status_code == 200
    assert client.post(f"/api/v1/projects/{sample_project_id}/assets/prepare").status_code == 200

    response = client.post(f"/api/v1/projects/{sample_project_id}/render")

    assert response.status_code == 200
    payload = response.json()
    assert payload["output_path"] == f"/tmp/{sample_project_id}/rendered-video.mp4"
    assert payload["asset_count"] == 8
    assert payload["idea_status"] == "rendered"

    render_asset = db_session.scalar(
        select(MediaAssetModel).where(
            MediaAssetModel.project_id == sample_project_id,
            MediaAssetModel.asset_type == "rendered_video",
        )
    )
    assert render_asset is not None
    assert render_asset.status == MediaAssetStatus.READY
    assert render_asset.storage_path == f"/tmp/{sample_project_id}/rendered-video.mp4"
    assert render_asset.metadata_json["renderer"] == "fake-renderer"
    assert render_asset.metadata_json["audio_embedded"] is True
    assert render_asset.metadata_json["background_music_embedded"] is True

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.idea.status == VideoIdeaStatus.RENDERED


def test_render_project_requires_prepared_assets(
    client: TestClient,
    sample_project_id: str,
) -> None:
    response = client.post(f"/api/v1/projects/{sample_project_id}/render")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Project '{sample_project_id}' must have prepared media assets before render."
    )


def test_ffmpeg_renderer_returns_clear_error_when_binary_is_missing() -> None:
    from pathlib import Path

    from app.adapters.rendering import FFmpegVideoRenderer, RenderInput

    renderer = FFmpegVideoRenderer(ffmpeg_binary="ffmpeg-binary-that-does-not-exist")
    output_dir = str(Path.cwd() / ".tmp-render-test")

    try:
        renderer.render(
            RenderInput(
                project_id="project-1",
                title="Titulo",
                script="Roteiro",
                asset_paths=["/tmp/a.txt"],
                output_dir=output_dir,
            )
        )
    except ValueError as exc:
        assert str(exc) == (
            "FFmpeg was not found. Install FFmpeg or set FFMPEG_BINARY in the environment."
        )
    else:
        raise AssertionError("Expected renderer to fail when FFmpeg binary is missing.")


def test_ffmpeg_renderer_returns_clear_error_when_process_fails() -> None:
    import subprocess
    from pathlib import Path
    from unittest.mock import patch

    from app.adapters.rendering import FFmpegVideoRenderer, RenderInput

    renderer = FFmpegVideoRenderer(ffmpeg_binary="ffmpeg")
    output_dir = str(Path.cwd() / ".tmp-render-test")

    with patch("app.adapters.rendering.subprocess.run") as mocked_run:
        mocked_run.side_effect = subprocess.CalledProcessError(
            1,
            ["ffmpeg"],
            stderr="mocked ffmpeg failure",
        )
        try:
            renderer.render(
                RenderInput(
                    project_id="project-1",
                title="Titulo",
                script="Roteiro",
                asset_paths=["/tmp/a.txt"],
                output_dir=output_dir,
            )
            )
        except ValueError as exc:
            assert str(exc) == "FFmpeg render failed. mocked ffmpeg failure"
        else:
            raise AssertionError("Expected renderer to fail when FFmpeg process fails.")


def test_ffmpeg_renderer_uses_voiceover_audio_when_available() -> None:
    from pathlib import Path
    from unittest.mock import patch

    from app.adapters.rendering import FFmpegVideoRenderer, RenderInput

    renderer = FFmpegVideoRenderer(ffmpeg_binary="ffmpeg")
    output_dir = str(Path.cwd() / ".tmp-render-test")

    with patch("app.adapters.rendering.subprocess.run") as mocked_run:
        result = renderer.render(
            RenderInput(
                project_id="project-1",
                title="Titulo",
                script="Roteiro com varios blocos.",
                asset_paths=["/tmp/a.txt", "/tmp/voiceover.wav", "/tmp/background-music.wav"],
                output_dir=output_dir,
                audio_path="/tmp/voiceover.wav",
                audio_duration_seconds=12.0,
                background_music_path="/tmp/background-music.wav",
            )
        )

    command = mocked_run.call_args.args[0]
    assert "/tmp/voiceover.wav" in command
    assert "/tmp/background-music.wav" in command
    assert "anullsrc=r=44100:cl=stereo" not in command
    assert result.metadata_json["audio_embedded"] is True
    assert result.metadata_json["background_music_embedded"] is True
    slide_count = result.metadata_json["slide_count"]
    assert isinstance(slide_count, int)
    assert slide_count >= 4
    timeline_sections = result.metadata_json["timeline_sections"]
    assert isinstance(timeline_sections, list)
    assert "REVISAO HUMANA" in timeline_sections
    assert any("CENA" in section for section in timeline_sections)
    assert "amix=inputs=2" in " ".join(command)
