from app.security import hash_password, issue_token, verify_password, verify_token


def test_password_hash_round_trip() -> None:
    encoded = hash_password("sufficiently-long-password")
    assert verify_password("sufficiently-long-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_session_token_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "a" * 32)
    token = issue_token(user_id="user-1", tenant_id="tenant-1")
    principal = verify_token(token)
    assert principal["sub"] == "user-1"
    assert principal["tenant"] == "tenant-1"


def test_session_token_rejects_tampering(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "a" * 32)
    token = issue_token(user_id="user-1", tenant_id="tenant-1")
    prefix, payload, signature = token.split(".")
    altered = f"{prefix}.{payload[:-1]}A.{signature}"
    try:
        verify_token(altered)
    except ValueError:
        pass
    else:  # pragma: no cover - makes failure explicit
        raise AssertionError("tampered token was accepted")
