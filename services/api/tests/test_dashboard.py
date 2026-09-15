from fastapi.testclient import TestClient

from app.main import app


def auth_headers(api_key: str = "dev-local-key") -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


client = TestClient(app)


def test_dashboard(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "dev-local-key")
    response = client.get("/dashboard", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "thread_count" in data
    assert "event_count" in data
    assert "outcome_count" in data
