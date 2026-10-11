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

        def claim_approved_send(self, tenant_id: str, actor_id: str, approval_id: str, idempotency_key: str):
            if idempotency_key in self.attempts:
                return {"attempt": self.attempts[idempotency_key], "payload": {}, "should_send": False}
            attempt = {"id": f"attempt-{idempotency_key}", "status": "queued"}
            self.attempts[idempotency_key] = attempt
            return {"attempt": attempt, "payload": {}, "should_send": True}

        def record_send_result(self, tenant_id: str, actor_id: str, attempt_id: str, *, message_id=None, error=None):
            attempt = next(item for item in self.attempts.values() if item["id"] == attempt_id)
            if error:
                attempt["status"] = "failed"
                self.failures.append(error)
            else:
                attempt["status"] = "sent"
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
