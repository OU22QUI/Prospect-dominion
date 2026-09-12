from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_page_renders_html() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Prospect Dominion" in response.text
