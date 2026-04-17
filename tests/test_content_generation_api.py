from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import VideoProjectModel, WorkflowRunModel
from app.domain.enums import JobStatus, VideoIdeaStatus


def test_generate_project_content_persists_generated_artifacts(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    response = client.post(f"/api/v1/projects/{sample_project_id}/content/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_name"] == "youtube_content_pipeline"
    assert payload["team_name"] == "youtube-content-team"
    assert payload["idea_status"] == "production_ready"

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.generated_briefing == "Briefing gerado para Ideia do projeto"
    assert project.generated_script == "Roteiro gerado para Descricao base da ideia"
    assert project.generated_title == "Ideia do projeto - titulo final"
    assert project.generated_description == "Descricao final para Descricao base da ideia"
    assert project.generated_tags == ["agno", "youtube", "mvp"]
    assert project.thumbnail_prompt == "Thumbnail com dashboard e CTA"
    assert project.production_plan == "Plano de producao final"
    assert project.idea.status == VideoIdeaStatus.PRODUCTION_READY

    workflow_runs = db_session.scalars(
        select(WorkflowRunModel).where(WorkflowRunModel.project_id == sample_project_id)
    ).all()
    assert len(workflow_runs) == 1
    assert workflow_runs[0].status == JobStatus.SUCCEEDED
    assert workflow_runs[0].workflow_name == "youtube_content_pipeline"
    assert workflow_runs[0].output_payload["team_name"] == "youtube-content-team"
