from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.media import PreparedMediaAsset
from app.db.models import MediaAssetModel, VideoProjectModel
from app.domain.enums import MediaAssetStatus, VideoIdeaStatus
from app.services.media_assets import MediaAssetPreparationService


def test_prepare_project_assets_persists_media_assets(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    generate_response = client.post(f"/api/v1/projects/{sample_project_id}/content/generate")
    assert generate_response.status_code == 200

    response = client.post(f"/api/v1/projects/{sample_project_id}/assets/prepare")

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_count"] == 8
    assert payload["asset_types"] == [
        "thumbnail",
        "thumbnail",
        "thumbnail",
        "voiceover_script",
        "voiceover_audio",
        "subtitles_srt",
        "subtitles_vtt",
        "background_music",
    ]
    assert payload["idea_status"] == "render_ready"

    assets = db_session.scalars(
        select(MediaAssetModel).where(MediaAssetModel.project_id == sample_project_id)
    ).all()
    assert len(assets) == 8
    assert assets[0].status == MediaAssetStatus.READY
    assert assets[0].source_adapter == "fake-media-adapter"

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.idea.status == VideoIdeaStatus.RENDER_READY


def test_prepare_project_assets_requires_generated_content(
    client: TestClient,
    sample_project_id: str,
) -> None:
    response = client.post(f"/api/v1/projects/{sample_project_id}/assets/prepare")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Project '{sample_project_id}' must have generated content before media preparation."
    )


def test_prepare_project_assets_truncates_long_source_reference(
    db_session: Session,
    sample_project_id: str,
) -> None:
    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    project.generated_script = "Roteiro pronto"
    project.thumbnail_prompt = "Prompt pronto"
    project.production_plan = "Plano pronto"
    db_session.commit()

    class LongReferenceAdapter:
        def prepare_assets(self, payload: object) -> list[PreparedMediaAsset]:
            return [
                PreparedMediaAsset(
                    asset_type="voiceover_script",
                    source_adapter="long-reference-adapter",
                    source_reference="x" * 900,
                    storage_path="/tmp/voiceover.txt",
                    metadata_json={},
                )
            ]

    service = MediaAssetPreparationService(adapter=LongReferenceAdapter())
    result = service.prepare_for_project(db_session, project_id=sample_project_id)

    assert result.asset_count == 1
    asset = db_session.scalar(
        select(MediaAssetModel).where(MediaAssetModel.project_id == sample_project_id)
    )
    assert asset is not None
    assert len(asset.source_reference) == 500
    assert asset.source_reference.endswith("...")
