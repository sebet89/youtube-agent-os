from fastapi.testclient import TestClient


def test_prepare_video_endpoint_runs_full_pipeline(
    client: TestClient,
    sample_project_id: str,
) -> None:
    response = client.post(f"/api/v1/projects/{sample_project_id}/prepare-video")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == sample_project_id
    assert payload["idea_status"] == "rendered"
    assert payload["executed_steps"] == ["content", "assets", "render"]
    assert payload["skipped_steps"] == []
    assert payload["rendered_video_path"] == f"/tmp/{sample_project_id}/rendered-video.mp4"


def test_prepare_video_endpoint_skips_steps_when_project_is_already_ready(
    client: TestClient,
    sample_project_id: str,
) -> None:
    first_response = client.post(f"/api/v1/projects/{sample_project_id}/prepare-video")
    assert first_response.status_code == 200

    second_response = client.post(f"/api/v1/projects/{sample_project_id}/prepare-video")

    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload["executed_steps"] == []
    assert payload["skipped_steps"] == ["content", "assets", "render"]
