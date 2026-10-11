from scripts import verify_deployment


def _compose_services():
    return {
        "api": {"State": "running", "Health": "healthy"},
        "caddy": {"State": "running"},
        "postgres": {"State": "running", "Health": "healthy"},
        "migrations": {"State": "exited", "ExitCode": "0"},
    }


def test_deployment_verifier_is_read_only_without_pilot_session(monkeypatch) -> None:
    monkeypatch.delenv("PD_PILOT_TOKEN", raising=False)
    monkeypatch.setattr(verify_deployment, "compose_services", _compose_services)
    monkeypatch.setattr(verify_deployment, "wait_for_ready", lambda timeout: {"status": "ready"})
    calls = []

    def fake_fetch(path, method="GET", payload=None, authenticated=True, bearer_token=None):
        calls.append((path, method, authenticated, bearer_token))
        if path == "/health":
            return 200, {"status": "ok"}
        if path == "/dashboard":
            return 401, {}
        if path == "/branding":
            return 200, {"brand_name": "Pilot"}
        if path == "/v1/me":
            return 401, {}
        raise AssertionError(f"unexpected verification request: {path}")

    monkeypatch.setattr(verify_deployment, "fetch", fake_fetch)

    result = verify_deployment.verify()

    assert result["status"] == "passed"
    assert result["pilot_checks"] == ["authentication_required"]
    assert all(method == "GET" for _, method, _, _ in calls)


def test_deployment_verifier_checks_pilot_reads_with_session(monkeypatch) -> None:
    monkeypatch.setenv("PD_PILOT_TOKEN", "pilot-session")
    monkeypatch.setattr(verify_deployment, "compose_services", _compose_services)
    monkeypatch.setattr(verify_deployment, "wait_for_ready", lambda timeout: {"status": "ready"})
    calls = []

    def fake_fetch(path, method="GET", payload=None, authenticated=True, bearer_token=None):
        calls.append((path, bearer_token))
        if path == "/health":
            return 200, {"status": "ok"}
        if path == "/dashboard":
            return 401, {}
        if path == "/branding":
            return 200, {"brand_name": "Pilot"}
        if path == "/v1/me":
            return 200, {"role": "operator"}
        if path in {"/v1/accounts", "/v1/priority-queue"}:
            return 200, {"items": []}
        raise AssertionError(f"unexpected verification request: {path}")

    monkeypatch.setattr(verify_deployment, "fetch", fake_fetch)

    result = verify_deployment.verify()

    assert result["pilot_checks"] == ["session", "accounts", "priority_queue"]
    assert {token for path, token in calls if path.startswith("/v1/")} == {"pilot-session"}
