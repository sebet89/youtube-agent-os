from fastapi.testclient import TestClient


def test_studio_dashboard_shows_empty_state_without_connections(client: TestClient) -> None:
    response = client.get("/api/v1/studio")

    assert response.status_code == 200
    assert "YouTube Agent OS" in response.text
    assert "Nenhum canal conectado ainda" in response.text
    assert "Criar projeto" in response.text
    assert "Projetos do studio" not in response.text
    assert "Configuracoes do sistema" in response.text


def test_studio_dashboard_lists_projects_and_channels(
    client: TestClient,
    sample_project_id: str,
) -> None:
    response = client.get("/api/v1/studio")

    assert response.status_code == 200
    assert "Project Channel" in response.text
    assert "Criar e preparar" in response.text
    assert sample_project_id not in response.text
    assert "Fluxo atual" in response.text
