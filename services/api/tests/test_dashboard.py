from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "thread_count" in data
    assert "event_count" in data
    assert "outcome_count" in data
