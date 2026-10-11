from app import main


def test_optional_services_do_not_block_pilot_readiness_by_default(monkeypatch) -> None:
    monkeypatch.delenv("PD_CHECK_QDRANT", raising=False)
    monkeypatch.delenv("PD_CHECK_REDIS", raising=False)
    monkeypatch.setattr(main, "httpx", None)
    monkeypatch.setattr(main, "redis", None)

    checks = main._readiness_checks()

    assert checks["qdrant"] == {"status": "unknown", "note": "optional service checks disabled"}
    assert checks["redis"] == {"status": "unknown", "note": "optional service checks disabled"}


def test_optional_services_are_checked_when_enabled(monkeypatch) -> None:
    class Response:
        status_code = 200

    class HttpClient:
        @staticmethod
        def get(url, timeout):
            assert url.endswith("/readyz")
            assert timeout == 3.0
            return Response()

    class RedisClient:
        @staticmethod
        def from_url(url, **kwargs):
            return RedisClient()

        def ping(self):
            return True

    class RedisModule:
        Redis = RedisClient

    monkeypatch.setenv("PD_CHECK_QDRANT", "true")
    monkeypatch.setenv("PD_CHECK_REDIS", "true")
    monkeypatch.setattr(main, "httpx", HttpClient)
    monkeypatch.setattr(main, "redis", RedisModule)

    checks = main._readiness_checks()

    assert checks["qdrant"]["status"] == "ok"
    assert checks["redis"]["status"] == "ok"
