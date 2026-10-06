from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_root() -> None:
    response = client.get("/api")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
