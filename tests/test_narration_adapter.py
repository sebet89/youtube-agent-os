from unittest.mock import patch

from app.adapters.narration import EdgeTTSNarrationProvider


def test_edge_tts_provider_returns_clear_error_when_package_is_missing() -> None:
    provider = EdgeTTSNarrationProvider()

    with patch("app.adapters.narration.importlib.import_module") as mocked_import:
        mocked_import.side_effect = ModuleNotFoundError("No module named 'edge_tts'")
        try:
            provider.synthesize(
                payload=type(
                    "Payload",
                    (),
                    {
                        "project_id": "project-1",
                        "title": "Titulo",
                        "script": "Primeira frase. Segunda frase.",
                        "output_path": ".tmp-edge/provider.wav",
                        "language": "pt-BR",
                    },
                )()
            )
        except ValueError as exc:
            assert "edge-tts is not installed" in str(exc)
        else:
            raise AssertionError(
                "Expected edge-tts provider to fail clearly when package is missing."
            )
