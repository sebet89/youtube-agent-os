import shutil
from pathlib import Path

from app.adapters.media import DeterministicMediaAssetAdapter, MediaPreparationInput
from app.adapters.narration import SyntheticNarrationProvider


def test_deterministic_media_adapter_creates_thumbnail_and_voiceover_files() -> None:
    output_root = Path.cwd() / ".tmp-media-adapter-test"
    if output_root.exists():
        shutil.rmtree(output_root)

    adapter = DeterministicMediaAssetAdapter(
        output_root=str(output_root),
        narration_provider=SyntheticNarrationProvider(),
    )

    assets = adapter.prepare_assets(
        MediaPreparationInput(
            project_id="project-1",
            generated_title="Titulo de teste",
            generated_script="Primeira cena. Segunda cena. Terceira cena.",
            thumbnail_prompt="Um dashboard cinematografico com CTA",
            production_plan="Abrir, explicar, encerrar.",
        )
    )

    thumbnail_assets = [asset for asset in assets if asset.asset_type == "thumbnail"]
    narration_asset = next(asset for asset in assets if asset.asset_type == "voiceover_audio")
    subtitles_srt_asset = next(asset for asset in assets if asset.asset_type == "subtitles_srt")
    subtitles_vtt_asset = next(asset for asset in assets if asset.asset_type == "subtitles_vtt")
    background_music_asset = next(
        asset for asset in assets if asset.asset_type == "background_music"
    )

    assert len(thumbnail_assets) == 3
    assert all(Path(asset.storage_path).exists() for asset in thumbnail_assets)
    assert Path(narration_asset.storage_path).exists()
    assert Path(subtitles_srt_asset.storage_path).exists()
    assert Path(subtitles_vtt_asset.storage_path).exists()
    assert Path(background_music_asset.storage_path).exists()
    assert thumbnail_assets[0].metadata_json["format"] == "svg"
    assert any(asset.metadata_json["selected"] is True for asset in thumbnail_assets)
    duration_seconds = narration_asset.metadata_json["duration_seconds"]
    assert isinstance(duration_seconds, (int, float))
    assert duration_seconds > 0
    assert subtitles_srt_asset.metadata_json["format"] == "srt"
    assert subtitles_vtt_asset.metadata_json["format"] == "vtt"
    assert background_music_asset.metadata_json["format"] == "wav"


def test_deterministic_media_adapter_sanitizes_windows_unsafe_filenames() -> None:
    output_root = Path.cwd() / ".tmp-media-adapter-test-windows-safe"
    if output_root.exists():
        shutil.rmtree(output_root)

    adapter = DeterministicMediaAssetAdapter(
        output_root=str(output_root),
        narration_provider=SyntheticNarrationProvider(),
    )

    assets = adapter.prepare_assets(
        MediaPreparationInput(
            project_id="project-unsafe",
            generated_title='Primeiro video utilizando o "Youtube Agent Os": fluxo assistido',
            generated_script="Cena um. Cena dois.",
            thumbnail_prompt="Thumbnail com CTA",
            production_plan="Abrir e concluir.",
        )
    )

    for asset in assets:
        path_name = Path(asset.storage_path).name
        assert ":" not in path_name
        assert '"' not in path_name
        assert Path(asset.storage_path).exists()
