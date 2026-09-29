"""Runs the complete pilot API path against a real Postgres database in CI.

Set PD_TEST_PG_DSN to a disposable database. This suite intentionally skips
outside that environment; it never guesses a database to erase or modify.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import psycopg
from fastapi.testclient import TestClient


PG_DSN = os.getenv("PD_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not PG_DSN, reason="requires disposable PD_TEST_PG_DSN")


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    root = Path(__file__).resolve().parents[3]
    env = {**os.environ, "PG_DSN": str(PG_DSN), "MIGRATIONS_DIR": str(root / "migrations" / "postgres")}
    result = subprocess.run([sys.executable, str(root / "services" / "migrations" / "apply.py")], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


@pytest.fixture(autouse=True)
def clean_disposable_database(migrated_database) -> None:
    with psycopg.connect(str(PG_DSN)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE tenants, users, bootstrap_guard CASCADE")


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("PD_STORE_BACKEND", "postgres")
    monkeypatch.setenv("PG_DSN", str(PG_DSN))
    monkeypatch.setenv("JWT_SECRET", "t" * 32)
    from app.main import app

    return TestClient(app)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_complete_governed_workflow(client, monkeypatch) -> None:
    from app import main

    class FakeResend:
        def send(self, payload):
            assert payload["to"] == "dana@acme.test"
            return "resend-message-1"

    monkeypatch.setattr(main, "ResendSender", FakeResend)
    monkeypatch.setattr(main, "verify_webhook", lambda raw, headers: None)
    bootstrap = client.post("/v1/auth/bootstrap", json={"tenant_slug": "e2e-pilot", "tenant_name": "E2E Pilot", "email": "owner@acme.test", "display_name": "Owner", "password": "a-password-long-enough"})
    assert bootstrap.status_code == 201, bootstrap.text
    token = bootstrap.json()["token"]
    csv_content = "external_id,domain,email,full_name,signal_type,observed_at,consent_basis\nsig-1,acme.test,dana@acme.test,Dana,intent.pricing,2026-01-01T00:00:00Z,consent\n"
    assert client.post("/v1/sources/csv/import", headers=auth(token), json={"source_name": "fixture", "content": csv_content}).status_code == 200
    rules = {"version": 1, "base_score": 25, "rules": [{"signal_type": "intent.pricing", "weight": 80, "max_age_days": 3650}]}
    assert client.put("/v1/settings/icp-rules", headers=auth(token), json={"rules": rules}).status_code == 200
    score = client.post("/v1/accounts/acme.test/score", headers=auth(token))
    assert score.status_code == 200, score.text
    assert client.get("/v1/priority-queue", headers=auth(token)).json()["items"][0]["action_type"] == "draft_outreach"
    threads = client.get("/v1/threads", headers=auth(token)).json()["items"]
    approval = client.post("/v1/approvals", headers=auth(token), json={"thread_id": threads[0]["thread_id"], "action_type": "draft_outreach", "idempotency_key": "approval-e2e-1", "action_payload": {"from": "Pilot <pilot@acme.test>", "to": "dana@acme.test", "subject": "Hello", "html": "<p>Hello</p>"}})
    assert approval.status_code == 201, approval.text
    approval_id = approval.json()["id"]
    viewer = client.post("/v1/users", headers=auth(token), json={"email": "viewer@acme.test", "display_name": "Viewer", "password": "viewer-password-long", "role": "viewer"})
    assert viewer.status_code == 201, viewer.text
    viewer_token = client.post("/v1/auth/login", json={"email": "viewer@acme.test", "password": "viewer-password-long"}).json()["token"]
    assert client.post(f"/v1/approvals/{approval_id}/approve", headers=auth(viewer_token), json={}).status_code == 403
    assert client.post(f"/v1/approvals/{approval_id}/send", headers=auth(token), json={"idempotency_key": "send-before-approval"}).status_code == 409
    assert client.post(f"/v1/approvals/{approval_id}/approve", headers=auth(token), json={}).status_code == 200
    sent = client.post(f"/v1/approvals/{approval_id}/send", headers=auth(token), json={"idempotency_key": "send-e2e-1"})
    assert sent.status_code == 200 and sent.json()["attempt"]["status"] == "sent"
    duplicate = client.post(f"/v1/approvals/{approval_id}/send", headers=auth(token), json={"idempotency_key": "send-e2e-1"})
    assert duplicate.json()["sent"] is False
    event = {"id": "evt-e2e-1", "type": "email.delivered", "data": {"email_id": "resend-message-1"}}
    webhook = client.post(f"/v1/webhooks/resend/{bootstrap.json()['tenant_id']}", content=json.dumps(event), headers={"content-type": "application/json"})
    assert webhook.status_code == 200 and webhook.json()["processed"] is True
    replay = client.post(f"/v1/webhooks/resend/{bootstrap.json()['tenant_id']}", content=json.dumps(event), headers={"content-type": "application/json"})
    assert replay.json()["processed"] is False
    outcomes = client.get("/v1/outcomes", headers=auth(token)).json()["items"]
    assert outcomes[0]["stage_to"] == "delivered"


def test_resend_webhook_cannot_target_another_tenant(client, monkeypatch) -> None:
    from app import main

    monkeypatch.setattr(main, "verify_webhook", lambda raw, headers: None)
    bootstrap = client.post("/v1/auth/bootstrap", json={"tenant_slug": "webhook-owner", "tenant_name": "Webhook Owner", "email": "owner@webhook.test", "display_name": "Owner", "password": "a-password-long-enough"})
    assert bootstrap.status_code == 201, bootstrap.text

    with psycopg.connect(str(PG_DSN)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO tenants (slug, display_name) VALUES ('webhook-other', 'Webhook Other') RETURNING id")
            other_tenant_id = str(cursor.fetchone()[0])

    event = {"id": "evt-cross-tenant", "type": "contact.unsubscribed", "data": {"email": "dana@acme.test"}}
    response = client.post(
        f"/v1/webhooks/resend/{other_tenant_id}",
        content=json.dumps(event),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 404

    with psycopg.connect(str(PG_DSN)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM suppression_entries WHERE tenant_id = %s", (other_tenant_id,))
            assert cursor.fetchone()[0] == 0


def test_tenant_isolation(client, monkeypatch) -> None:
    from app.security import hash_password, issue_token

    with psycopg.connect(str(PG_DSN)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO tenants (slug, display_name) VALUES ('isolated-pilot', 'Isolated Pilot') RETURNING id")
            tenant_id = str(cursor.fetchone()[0])
            cursor.execute("INSERT INTO users (email, display_name, password_hash) VALUES ('isolated@acme.test', 'Isolated', %s) RETURNING id", (hash_password("isolated-password-long"),))
            user_id = str(cursor.fetchone()[0])
            cursor.execute("SELECT id FROM roles WHERE name = 'owner'")
            cursor.execute("INSERT INTO workspace_memberships (tenant_id, user_id, role_id) VALUES (%s, %s, (SELECT id FROM roles WHERE name = 'owner'))", (tenant_id, user_id))
        connection.commit()
    token = issue_token(user_id=user_id, tenant_id=tenant_id)
    response = client.get("/v1/accounts", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["items"] == []
