from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PipelineJobModel, VideoProjectModel
from app.domain.enums import JobStatus, VideoIdeaStatus
from app.services.content_generation import ContentGenerationService
from app.services.media_assets import MediaAssetPreparationService
from app.services.pipeline import execute_project_pipeline
from app.services.rendering import VideoRenderingService
from tests.conftest import (
    FakeContentWorkflowProvider,
    FakeMediaAssetAdapter,
    FakeVideoRenderer,
)


def test_queue_project_pipeline_creates_pending_job(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    response = client.post(f"/api/v1/projects/{sample_project_id}/pipeline/queue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["queue_name"] == "pipeline"
    assert payload["celery_task_id"] == f"celery-{sample_project_id}"

    job = db_session.scalar(
        select(PipelineJobModel).where(PipelineJobModel.id == payload["pipeline_job_id"])
    )
    assert job is not None
    assert job.project_id == sample_project_id
    assert job.status == JobStatus.PENDING
    assert job.job_type == "project_pipeline"


def test_list_project_jobs_returns_enqueued_job(
    client: TestClient,
    sample_project_id: str,
) -> None:
    queue_response = client.post(f"/api/v1/projects/{sample_project_id}/pipeline/queue")
    assert queue_response.status_code == 200

    response = client.get(f"/api/v1/projects/{sample_project_id}/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == sample_project_id
    assert len(payload["jobs"]) == 1
    assert payload["jobs"][0]["job_type"] == "project_pipeline"
    assert payload["jobs"][0]["status"] == "pending"


def test_execute_project_pipeline_runs_all_stages(
    db_session: Session,
    sample_project_id: str,
) -> None:
    result = execute_project_pipeline(
        db_session,
        project_id=sample_project_id,
        content_service=ContentGenerationService(provider=FakeContentWorkflowProvider()),
        media_service=MediaAssetPreparationService(adapter=FakeMediaAssetAdapter()),
        render_service=VideoRenderingService(
            renderer=FakeVideoRenderer(),
            output_root="/tmp/test-renders",
        ),
    )

    assert result["project_id"] == sample_project_id
    assert result["idea_status"] == "rendered"
    assert result["output_path"] == f"/tmp/{sample_project_id}/rendered-video.mp4"

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.idea.status == VideoIdeaStatus.RENDERED
