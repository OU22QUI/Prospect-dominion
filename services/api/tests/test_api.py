from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_thread_and_fetch() -> None:
    response = client.post(
        "/threads",
        json={"person_id": "person-1", "account_id": "acct-1", "campaign_id": "camp-1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["person_id"] == "person-1"

    fetch_response = client.get("/threads")
    assert fetch_response.status_code == 200
    assert any(item["thread_id"] == body["thread_id"] for item in fetch_response.json())
