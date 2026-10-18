from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_workflow_service() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "contentops-api",
        "database": "sqlite",
    }


def test_removed_generation_routes_stay_removed() -> None:
    assert client.post("/generate", json={"idea": "No provider path."}).status_code == 404
    assert client.post("/revise", json={"idea": "No provider path."}).status_code == 404
