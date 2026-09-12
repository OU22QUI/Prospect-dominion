from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_orchestration_route() -> None:
    response = client.get("/orchestration/thread_123")
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "thread_123"
    assert body["status"] == "ready"
    assert len(body["pipeline"]) > 0
