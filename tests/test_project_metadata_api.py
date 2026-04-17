from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import MediaAssetModel, VideoProjectModel
from app.domain.enums import MediaAssetStatus


def test_update_project_metadata_persists_changes(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    response = client.patch(
        f"/api/v1/projects/{sample_project_id}/metadata",
        json={
            "generated_title": "Titulo refinado para publicacao",
            "generated_description": "Descricao ajustada pela revisao humana.",
            "generated_tags": ["youtube", "mvp", "youtube"],
            "thumbnail_prompt": "Thumbnail mais clara com CTA forte",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_title"] == "Titulo refinado para publicacao"
    assert payload["generated_description"] == "Descricao ajustada pela revisao humana."
    assert payload["generated_tags"] == ["youtube", "mvp"]
    assert payload["thumbnail_prompt"] == "Thumbnail mais clara com CTA forte"

    project = db_session.get(VideoProjectModel, sample_project_id)
    assert project is not None
    assert project.generated_title == "Titulo refinado para publicacao"
    assert project.generated_description == "Descricao ajustada pela revisao humana."
    assert project.generated_tags == ["youtube", "mvp"]
    assert project.thumbnail_prompt == "Thumbnail mais clara com CTA forte"


def test_select_thumbnail_variant_marks_asset_as_selected(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    hero_asset = MediaAssetModel(
        project_id=sample_project_id,
        asset_type="thumbnail",
        source_adapter="test-suite",
        source_reference="prompt",
        storage_path="C:/thumbs/hero.svg",
        status=MediaAssetStatus.READY,
        metadata_json={"variant": "hero", "selected": True},
    )
    minimal_asset = MediaAssetModel(
        project_id=sample_project_id,
        asset_type="thumbnail",
        source_adapter="test-suite",
        source_reference="prompt",
        storage_path="C:/thumbs/minimal.svg",
        status=MediaAssetStatus.READY,
        metadata_json={"variant": "minimal", "selected": False},
    )
    db_session.add_all([hero_asset, minimal_asset])
    db_session.commit()

    response = client.patch(
        f"/api/v1/projects/{sample_project_id}/thumbnail-selection",
        json={"asset_id": minimal_asset.id},
    )

    assert response.status_code == 200
    db_session.refresh(hero_asset)
    db_session.refresh(minimal_asset)
    assert hero_asset.metadata_json["selected"] is False
    assert minimal_asset.metadata_json["selected"] is True


def test_project_artifact_routes_serve_rendered_video_and_thumbnail(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    temp_dir = Path.cwd() / ".runtime" / "test-artifacts" / sample_project_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    rendered_file = temp_dir / "rendered-video.mp4"
    rendered_file.write_bytes(b"fake-mp4")
    thumbnail_file = temp_dir / "thumbnail.svg"
    thumbnail_file.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

    db_session.add_all(
        [
            MediaAssetModel(
                project_id=sample_project_id,
                asset_type="rendered_video",
                source_adapter="test-suite",
                source_reference="render",
                storage_path=str(rendered_file),
                status=MediaAssetStatus.READY,
                metadata_json={},
            ),
            MediaAssetModel(
                project_id=sample_project_id,
                asset_type="thumbnail",
                source_adapter="test-suite",
                source_reference="thumbnail",
                storage_path=str(thumbnail_file),
                status=MediaAssetStatus.READY,
                metadata_json={"selected": True},
            ),
        ]
    )
    db_session.commit()

    video_response = client.get(f"/api/v1/projects/{sample_project_id}/artifacts/rendered-video")
    thumbnail_response = client.get(f"/api/v1/projects/{sample_project_id}/artifacts/thumbnail")

    assert video_response.status_code == 200
    assert video_response.content == b"fake-mp4"
    assert video_response.headers["content-type"] == "video/mp4"
    assert thumbnail_response.status_code == 200
    assert "<svg" in thumbnail_response.text
    assert thumbnail_response.headers["content-type"].startswith("image/svg+xml")
