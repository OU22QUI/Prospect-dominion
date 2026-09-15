import pytest
from fastapi.testclient import TestClient

from app.main import app, get_expected_api_key


def auth_headers(api_key: str = "dev-local-key") -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["service"] == "prospect-dominion-api"


def test_create_thread_and_fetch(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "dev-local-key")
    response = client.post(
        "/threads",
        json={"person_id": "person-1", "account_id": "acct-1", "campaign_id": "camp-1"},
        headers=auth_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["person_id"] == "person-1"

    fetch_response = client.get("/threads", headers=auth_headers())
    assert fetch_response.status_code == 200
    assert any(item["thread_id"] == body["thread_id"] for item in fetch_response.json())


def test_advance_thread_stage(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "dev-local-key")
    response = client.post(
        "/threads",
        json={"person_id": "person-advance", "account_id": "acct-advance", "campaign_id": "camp-advance"},
        headers=auth_headers(),
    )
    assert response.status_code == 201
    thread_id = response.json()["thread_id"]

    advance = client.post(
        f"/threads/{thread_id}/advance",
        json={"event_type": "reply.positive", "source": "demo"},
        headers=auth_headers(),
    )
    assert advance.status_code == 200
    payload = advance.json()
    assert payload["thread_id"] == thread_id
    assert payload["current_stage"] in ["reply.positive", "meeting.booked", "outcome.logged"]


def test_record_event_and_advance_stage(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "dev-local-key")
    response = client.post(
        "/threads",
        json={"person_id": "person-event", "account_id": "acct-event", "campaign_id": "camp-event"},
        headers=auth_headers(),
    )
    assert response.status_code == 201
    thread_id = response.json()["thread_id"]

    result = client.post(
        f"/threads/{thread_id}/events",
        json={"event_type": "reply.positive", "source": "demo", "payload": {"channel": "email"}},
        headers=auth_headers(),
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["thread_id"] == thread_id
    assert payload["event"]["event_type"] == "reply.positive"
    assert payload["thread_state"]["current_stage"] in ["reply.positive", "meeting.booked", "outcome.logged"]


def test_protected_routes_require_api_key(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "test-api-key")
    response = client.get("/threads")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_valid_api_key_allows_access(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "test-api-key")
    auth_client = TestClient(app)
    response = auth_client.get("/threads", headers={"Authorization": "Bearer test-api-key"})
    assert response.status_code == 200


def test_production_requires_explicit_api_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PD_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="PD_API_KEY"):
        get_expected_api_key()


def test_run_local_redacts_api_key_in_banner(monkeypatch) -> None:
    import run_local

    masked = run_local.describe_key_state("super-secret-key")
    assert "super-secret-key" not in masked
    assert "configured" in masked.lower()


def test_set_api_key_in_environment_for_local_usage(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "dev-local-key")
    local_client = TestClient(app)
    response = local_client.get("/threads", headers={"Authorization": "Bearer dev-local-key"})
    assert response.status_code == 200


def test_branding_config_uses_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("PD_BRAND_NAME", "Northstar Revenue")
    monkeypatch.setenv("PD_BRAND_TAGLINE", "Revenue intelligence for teams")
    monkeypatch.setenv("PD_PRIMARY_COLOR", "#7cf0b3")

    response = client.get("/branding")
    assert response.status_code == 200
    payload = response.json()
    assert payload["brand_name"] == "Northstar Revenue"
    assert payload["brand_tagline"] == "Revenue intelligence for teams"
    assert payload["primary_color"] == "#7cf0b3"

    html = client.get("/").text
    assert "Northstar Revenue" in html


def test_store_project_root_resolution() -> None:
    from pathlib import Path

    from app import stores

    root = stores.resolve_project_root()
    assert isinstance(root, Path)
    assert root.is_absolute()
    assert (root / "docker-compose.yml").exists() or (root / "README.md").exists() or (root / ".git").exists()


def test_resolve_project_root_handles_container_layout(monkeypatch, tmp_path) -> None:
    from app import stores

    project_root = tmp_path / "project-root"
    project_root.mkdir()
    (project_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    app_dir = project_root / "services" / "api" / "app"
    app_dir.mkdir(parents=True)
    (app_dir / "__init__.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(stores, "__file__", str(app_dir / "stores.py"))
    monkeypatch.chdir(project_root)

    resolved = stores.resolve_project_root()
    assert resolved == project_root


def test_runtime_config_validation_rejects_missing_required_values(monkeypatch) -> None:
    monkeypatch.delenv("PD_API_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    from app.main import validate_runtime_config

    result = validate_runtime_config()
    assert result["status"] == "invalid"
    assert "PD_API_KEY" in result["issues"]
