import socket

from app.main import resolve_runtime_port


def test_resolve_runtime_port_uses_env_override(monkeypatch) -> None:
    monkeypatch.setenv("PD_PORT", "8123")
    assert resolve_runtime_port() == 8123


def test_resolve_runtime_port_falls_back_to_next_free_port(monkeypatch) -> None:
    monkeypatch.delenv("PD_PORT", raising=False)

    taken_port = 65534
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", taken_port))
    sock.listen(1)
    try:
        assert resolve_runtime_port(default_port=taken_port) == taken_port + 1
    finally:
        sock.close()
