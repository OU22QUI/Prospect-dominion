import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main
from app.security import issue_token


def test_send_failure_is_recorded_and_retry_is_explicit(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "t" * 32)

    class FakePilotStore:
        attempts: dict[str, dict[str, str]]
        failures: list[str]

        def __init__(self) -> None:
            self.attempts = {}
            self.failures = []

        def principal(self, user_id: str, tenant_id: str) -> dict[str, str]:
            return {"user_id": user_id, "tenant_id": tenant_id, "role": "owner"}

        def claim_approved_send(self, tenant_id: str, actor_id: str, approval_id: str, idempotency_key: str, provider: str = "resend"):
            if idempotency_key in self.attempts:
                return {"attempt": self.attempts[idempotency_key], "payload": {}, "should_send": False}
            attempt = {"id": f"attempt-{idempotency_key}", "status": "queued", "provider": provider}
            self.attempts[idempotency_key] = attempt
            return {"attempt": attempt, "payload": {}, "should_send": True}

        def record_send_result(self, tenant_id: str, actor_id: str, attempt_id: str, *, message_id=None, error=None, simulated=False):
            attempt = next(item for item in self.attempts.values() if item["id"] == attempt_id)
            if error:
                attempt["status"] = "failed"
                self.failures.append(error)
            else:
                attempt["status"] = "simulated" if simulated else "sent"
                attempt["provider_message_id"] = message_id
            return attempt

    store = FakePilotStore()
    monkeypatch.setattr(main, "get_pilot_store", lambda: store)
    send_calls: list[int] = []

    class FailThenSucceedSender:
        def send(self, payload):
            send_calls.append(1)
            if len(send_calls) == 1:
                raise RuntimeError("provider unavailable")
            return "resend-message-1"

    monkeypatch.setattr(main, "ResendSender", FailThenSucceedSender)
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {issue_token(user_id='user-1', tenant_id='tenant-1')}"}

    failed = client.post("/v1/approvals/approval-1/send", headers=headers, json={"idempotency_key": "attempt-fail"})

    assert failed.status_code == 502
    assert failed.json()["detail"] == "Outbound send failed; attempt attempt-attempt-fail was recorded. Review it before retrying."
    assert "provider unavailable" not in failed.text
    assert store.failures == ["provider unavailable"]

    replay = client.post("/v1/approvals/approval-1/send", headers=headers, json={"idempotency_key": "attempt-fail"})
    assert replay.status_code == 200
    assert replay.json()["sent"] is False
    assert replay.json()["attempt"]["status"] == "failed"
    assert len(send_calls) == 1

    retry = client.post("/v1/approvals/approval-1/send", headers=headers, json={"idempotency_key": "attempt-retry"})
    assert retry.status_code == 200
    assert retry.json()["sent"] is True
    assert retry.json()["attempt"]["status"] == "sent"
    assert len(send_calls) == 2


def test_mock_provider_records_simulation_without_using_resend(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "t" * 32)
    monkeypatch.setenv("PD_ACTION_PROVIDER", "mock")

    class FakePilotStore:
        def __init__(self) -> None:
            self.attempt = {"id": "attempt-simulated", "status": "queued", "provider": None}

        def principal(self, user_id: str, tenant_id: str) -> dict[str, str]:
            return {"user_id": user_id, "tenant_id": tenant_id, "role": "owner"}

        def claim_approved_send(self, tenant_id, actor_id, approval_id, idempotency_key, provider="resend"):
            self.attempt["provider"] = provider
            return {
                "attempt": self.attempt,
                "payload": {"from": "Demo <demo@example.test>", "to": "person@example.test", "subject": "Demo", "html": "<p>Demo</p>"},
                "should_send": True,
            }

        def record_send_result(self, tenant_id, actor_id, attempt_id, *, message_id=None, error=None, simulated=False):
            self.attempt["status"] = "simulated" if simulated else "sent"
            return self.attempt

    store = FakePilotStore()
    monkeypatch.setattr(main, "get_pilot_store", lambda: store)
    monkeypatch.setattr(main, "ResendSender", lambda: (_ for _ in ()).throw(AssertionError("Resend must not be constructed in mock mode")))
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {issue_token(user_id='user-1', tenant_id='tenant-1')}"}

    response = client.post("/v1/approvals/approval-1/send", headers=headers, json={"idempotency_key": "attempt-simulated"})

    assert response.status_code == 200
    assert response.json()["sent"] is False
    assert response.json()["simulated"] is True
    assert response.json()["attempt"]["status"] == "simulated"
    assert response.json()["attempt"]["provider"] == "simulation"


def test_production_rejects_mock_action_provider(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PD_ACTION_PROVIDER", "mock")

    with pytest.raises(HTTPException) as exc:
        main.get_action_provider_mode()

    assert exc.value.status_code == 503


def test_pilot_store_contract_signatures() -> None:
    import inspect
    from app.pilot_store import PilotStore

    claim_sig = inspect.signature(PilotStore.claim_approved_send)
    assert "provider" in claim_sig.parameters
    assert claim_sig.parameters["provider"].default == "resend"

    record_sig = inspect.signature(PilotStore.record_send_result)
    assert "simulated" in record_sig.parameters
    assert record_sig.parameters["simulated"].default is False
