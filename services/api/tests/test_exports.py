from app.exports import audit_proof


def test_audit_proof_removes_email_addresses() -> None:
    proof = audit_proof([{"occurred_at": "2026-01-01", "event_type": "send.sent", "entity_type": "send", "entity_id": "1", "details": {"email": "Dana@Acme.test", "note": "Sent dana@acme.test"}}])
    rendered = str(proof)
    assert "dana@acme.test" not in rendered.lower()
    assert "contact-" in rendered
