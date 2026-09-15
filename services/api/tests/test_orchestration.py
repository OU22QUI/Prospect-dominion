from fastapi.testclient import TestClient

from app.main import app


def auth_headers(api_key: str = "dev-local-key") -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


client = TestClient(app)


def test_orchestration_route(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "dev-local-key")
    response = client.get("/orchestration/thread_123", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "thread_123"
    assert body["status"] == "ready"
    assert len(body["pipeline"]) > 0
