from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProjectEventModel, VideoIdeaModel, VideoProjectModel
from app.domain.enums import ReviewStatus, VideoIdeaStatus, VideoVisibility


def test_create_project_creates_idea_and_project(
    client: TestClient,
    db_session: Session,
) -> None:
    oauth_response = client.get(
        "/api/v1/oauth/youtube/callback",
        params={
            "state": client.get("/api/v1/oauth/youtube/authorize").json()["state"],
            "code": "good-code",
        },
    )
    assert oauth_response.status_code == 200
    connection_id = oauth_response.json()["connection_id"]

    response = client.post(
        "/api/v1/projects",
        json={
            "connection_id": connection_id,
            "title": "Como usar youtube-agent-os",
            "raw_idea": "Mostrar o fluxo do MVP do inicio ao fim.",
            "target_audience": "Devs e criadores",
            "business_goal": "Validar produto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["connection_id"] == connection_id
    assert payload["title"] == "Como usar youtube-agent-os"
    assert payload["idea_status"] == "draft"
    assert payload["visibility"] == "private"
    assert payload["review_status"] == "pending"
    assert payload["review_url"].endswith(f"/api/v1/review/projects/{payload['project_id']}")

    idea = db_session.scalar(
        select(VideoIdeaModel).where(VideoIdeaModel.id == payload["idea_id"])
    )
    assert idea is not None
    assert idea.status == VideoIdeaStatus.DRAFT
    assert idea.target_audience == "Devs e criadores"
    assert idea.business_goal == "Validar produto"

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == payload["project_id"])
    )
    assert project is not None
    assert project.visibility == VideoVisibility.PRIVATE
    assert project.review_status == ReviewStatus.PENDING

    project_event = db_session.scalar(
        select(ProjectEventModel).where(
            ProjectEventModel.project_id == payload["project_id"],
            ProjectEventModel.event_type == "project_created",
        )
    )
    assert project_event is not None
    assert project_event.message == "Projeto criado e pronto para iniciar a producao."


def test_create_project_rejects_unknown_connection(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects",
        json={
            "connection_id": "missing-connection",
            "title": "Titulo",
            "raw_idea": "Ideia base",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Channel connection 'missing-connection' was not found."
