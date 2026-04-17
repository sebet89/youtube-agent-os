from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AnalyticsSnapshotModel


def test_collect_project_analytics_persists_snapshot(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    upload_response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )
    assert upload_response.status_code == 200

    response = client.post(f"/api/v1/projects/{sample_project_id}/analytics/collect")

    assert response.status_code == 200
    payload = response.json()
    assert payload["view_count"] == 321
    assert payload["like_count"] == 45
    assert payload["comment_count"] == 6

    snapshot = db_session.scalar(
        select(AnalyticsSnapshotModel).where(
            AnalyticsSnapshotModel.project_id == sample_project_id
        )
    )
    assert snapshot is not None
    assert snapshot.youtube_video_id == "yt-uploaded-1"
    assert snapshot.view_count == 321


def test_collect_project_analytics_requires_uploaded_video(
    client: TestClient,
    sample_project_id: str,
) -> None:
    response = client.post(f"/api/v1/projects/{sample_project_id}/analytics/collect")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Project must be uploaded to YouTube before collecting analytics."
    )


def test_list_project_analytics_returns_latest_snapshots(
    client: TestClient,
    sample_project_id: str,
) -> None:
    upload_response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )
    assert upload_response.status_code == 200

    collect_response = client.post(f"/api/v1/projects/{sample_project_id}/analytics/collect")
    assert collect_response.status_code == 200

    response = client.get(f"/api/v1/projects/{sample_project_id}/analytics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == sample_project_id
    assert len(payload["snapshots"]) == 1
    assert payload["snapshots"][0]["youtube_video_id"] == "yt-uploaded-1"
    assert payload["snapshots"][0]["view_count"] == 321
