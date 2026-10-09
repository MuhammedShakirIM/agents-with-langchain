from fastapi.testclient import TestClient

from learning_companion.main import app


def test_health():
    response = TestClient(app).get("/health")
    assert response.json() == {"status": "ok"}
