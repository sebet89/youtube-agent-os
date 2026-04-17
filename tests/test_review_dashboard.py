from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_review_dashboard_renders_project_summary(
    client: TestClient,
    sample_project_id: str,
) -> None:
    response = client.get(f"/api/v1/review/projects/{sample_project_id}")

    assert response.status_code == 200
    assert "Painel de revisao humana" in response.text
    assert "Preparar video automaticamente" in response.text
    assert "Editar metadados" in response.text
    assert "Preview de legenda" in response.text
    assert "Aprovar publicacao" in response.text
    assert "Rejeitar publicacao" in response.text
    assert sample_project_id in response.text


def test_review_dashboard_reflects_rejected_status(
    client: TestClient,
    sample_project_id: str,
) -> None:
    reject_response = client.post(
        f"/api/v1/projects/{sample_project_id}/review/reject",
        json={"reviewer_name": "qa-reviewer", "notes": "Ajustar CTA"},
    )
    assert reject_response.status_code == 200

    response = client.get(f"/api/v1/review/projects/{sample_project_id}")

    assert response.status_code == 200
    assert "Review: rejected" in response.text


def test_review_dashboard_shows_rendered_video_after_pipeline_execution(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    from app.services.content_generation import ContentGenerationService
    from app.services.media_assets import MediaAssetPreparationService
    from app.services.pipeline import execute_project_pipeline
    from app.services.rendering import VideoRenderingService
    from tests.conftest import (
        FakeContentWorkflowProvider,
        FakeMediaAssetAdapter,
        FakeVideoRenderer,
    )

    execute_project_pipeline(
        db_session,
        project_id=sample_project_id,
        content_service=ContentGenerationService(provider=FakeContentWorkflowProvider()),
        media_service=MediaAssetPreparationService(adapter=FakeMediaAssetAdapter()),
        render_service=VideoRenderingService(
            renderer=FakeVideoRenderer(),
            output_root="/tmp/test-renders",
        ),
    )

    response = client.get(f"/api/v1/review/projects/{sample_project_id}")

    assert response.status_code == 200
    assert f"/tmp/{sample_project_id}/rendered-video.mp4" in response.text
    assert f"/api/v1/projects/{sample_project_id}/artifacts/rendered-video" in response.text
    assert f"/api/v1/projects/{sample_project_id}/artifacts/thumbnail" in response.text
    assert "Briefing, roteiro e metadados foram gerados." in response.text
    assert "Assets de midia foram preparados para o render." in response.text
    assert "Video final renderizado e pronto para revisao." in response.text


def test_review_dashboard_shows_latest_analytics(
    client: TestClient,
    sample_project_id: str,
) -> None:
    upload_response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )
    assert upload_response.status_code == 200

    analytics_response = client.post(f"/api/v1/projects/{sample_project_id}/analytics/collect")
    assert analytics_response.status_code == 200

    response = client.get(f"/api/v1/review/projects/{sample_project_id}")

    assert response.status_code == 200
    assert "views 321 | likes 45 | comentarios 6" in response.text
    assert "Analytics basicos do video foram atualizados." in response.text


def test_review_dashboard_shows_uploaded_youtube_package_status(
    client: TestClient,
    sample_project_id: str,
) -> None:
    assert client.post(f"/api/v1/projects/{sample_project_id}/content/generate").status_code == 200
    assert client.post(f"/api/v1/projects/{sample_project_id}/assets/prepare").status_code == 200
    upload_response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )
    assert upload_response.status_code == 200

    response = client.get(f"/api/v1/review/projects/{sample_project_id}")

    assert response.status_code == 200
    assert "Thumbnail selecionada ja enviada ao YouTube" in response.text
    assert "Legenda enviada ao YouTube (pt-BR)" in response.text
    assert "Video enviado ao YouTube como private." in response.text


def test_review_dashboard_shows_scheduled_publication(
    client: TestClient,
    sample_project_id: str,
) -> None:
    assert (
        client.post(
            f"/api/v1/projects/{sample_project_id}/youtube/upload",
            json={"file_path": "C:/videos/output.mp4"},
        ).status_code
        == 200
    )
    assert client.post(
        f"/api/v1/projects/{sample_project_id}/review/approve",
        json={"reviewer_name": "human-reviewer", "notes": "Agendar"},
    ).status_code == 200
    assert client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/schedule",
        json={"publish_at": "2030-01-01T12:00:00+00:00"},
    ).status_code == 200

    response = client.get(f"/api/v1/review/projects/{sample_project_id}")

    assert response.status_code == 200
    assert "Agendado:" in response.text
    assert "Agendar ou reagendar" in response.text
    assert "Cancelar agendamento" in response.text
    assert "Linha do tempo operacional" in response.text


def test_review_dashboard_shows_pipeline_job_timeline(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    from app.services.pipeline import (
        PipelineJobService,
        mark_pipeline_job_running,
        mark_pipeline_job_succeeded,
    )
    from tests.conftest import FakePipelineDispatcher

    service = PipelineJobService(dispatcher=FakePipelineDispatcher())
    dispatch = service.enqueue_project_pipeline(db_session, project_id=sample_project_id)
    mark_pipeline_job_running(db_session, dispatch.pipeline_job_id)
    mark_pipeline_job_succeeded(db_session, dispatch.pipeline_job_id)

    response = client.get(f"/api/v1/review/projects/{sample_project_id}")

    assert response.status_code == 200
    assert "Pipeline completo foi enviado para processamento em background." in response.text
    assert "Pipeline em background iniciou a execucao do projeto." in response.text
    assert "Pipeline em background concluiu com sucesso." in response.text
