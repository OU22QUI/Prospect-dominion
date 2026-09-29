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


def test_ready_checks_postgres_when_pilot_backend_is_postgres(monkeypatch) -> None:
    from app import main

    class UnavailablePilotStore:
        def transaction(self):
            raise RuntimeError("database unavailable")

    monkeypatch.setenv("PD_STORE_BACKEND", "postgres")
    monkeypatch.setattr(main, "get_pilot_store", UnavailablePilotStore)
    response = client.get("/ready")
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["database"]["status"] == "unavailable"


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


def test_x_role_header_cannot_escalate_api_key_role(monkeypatch) -> None:
    monkeypatch.setenv("PD_API_KEY", "role-test-key")
    monkeypatch.setenv("PD_DEFAULT_ROLE", "viewer")
    response = client.post(
        "/threads",
        json={"person_id": "person-role", "account_id": "acct-role"},
        headers={"Authorization": "Bearer role-test-key", "X-Role": "admin"},
    )
    assert response.status_code == 403


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


def test_production_runtime_rejects_weak_jwt_and_missing_resend(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PD_API_KEY", "prod-" + "a" * 32)
    monkeypatch.setenv("JWT_SECRET", "change-me")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://pilot.example.com")
    monkeypatch.setenv("PD_STORE_BACKEND", "sqlite")
    for key in ("PG_DSN", "PD_PUBLIC_HOST", "PD_CADDYFILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    from app.main import validate_runtime_config

    result = validate_runtime_config()
    assert result["status"] == "invalid"
    assert "JWT_SECRET_STRENGTH" in result["issues"]
    assert "PD_STORE_BACKEND_POSTGRES" in result["issues"]
    assert "PG_DSN" in result["issues"]
    assert "PD_PUBLIC_HOST" in result["issues"]
    assert "PD_CADDYFILE" in result["issues"]
    assert "RESEND_API_KEY" in result["issues"]
    assert "RESEND_WEBHOOK_SECRET" in result["issues"]


def test_production_default_role_is_least_privilege(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PD_DEFAULT_ROLE", raising=False)
    from app.main import get_default_role

    assert get_default_role() == "viewer"


def test_complete_production_runtime_config_is_valid(monkeypatch) -> None:
    import base64

    values = {
        "APP_ENV": "production",
        "PD_API_KEY": "prod-" + "a" * 32,
        "PD_DEFAULT_ROLE": "viewer",
        "JWT_SECRET": "j" * 48,
        "PUBLIC_BASE_URL": "https://pilot.example.com",
        "PG_DSN": "postgresql://pilot:secret@postgres:5432/prospect_dominion",
        "PD_STORE_BACKEND": "postgres",
        "PD_PUBLIC_HOST": "pilot.example.com",
        "PD_CADDYFILE": "./infra/caddy/Caddyfile.production",
        "RESEND_API_KEY": "re_" + "r" * 32,
        "RESEND_WEBHOOK_SECRET": "whsec_" + base64.b64encode(b"s" * 32).decode().rstrip("="),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    from app.main import validate_runtime_config

    assert validate_runtime_config()["status"] == "valid"


def test_operator_app_serves_html() -> None:
    response = client.get("/app")
    assert response.status_code == 200
    assert "Pilot operator" in response.text
    assert "Revenue operations" in response.text
    assert "kpiRow" in response.text
    assert "Priority queue" in response.text


def test_v1_auth_required() -> None:
    response = client.get("/v1/me")
    assert response.status_code == 401
