from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "services" / "api"
PORT = int(os.getenv("PD_PORT", "8123"))
BASE_URL = f"http://127.0.0.1:{PORT}"
API_KEY = os.getenv("PD_API_KEY", "dev-local-key")


def fetch_json(url: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict | list | None]:
    data = None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {API_KEY}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            if not body:
                return response.status, {}
            return response.status, json.loads(body)
    except HTTPError as exc:  # pragma: no cover - network validation path
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, {"error": body}
    except URLError as exc:  # pragma: no cover - network validation path
        raise RuntimeError(f"Unable to reach {url}: {exc}") from exc


def wait_for_ready(process: subprocess.Popen[str], timeout_seconds: int = 45) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"api exited early with code {process.returncode}")
        try:
            status, payload = fetch_json(f"{BASE_URL}/ready")
            if status == 200 and payload and payload.get("status") == "ready":
                return
        except RuntimeError:
            pass
        time.sleep(1)
    raise TimeoutError(f"API never became ready at {BASE_URL}")


def main() -> int:
    env = os.environ.copy()
    env["PD_PORT"] = str(PORT)
    env["PD_API_KEY"] = API_KEY
    process = subprocess.Popen(
        [sys.executable, "run_local.py"],
        cwd=str(API_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for_ready(process)
        status, ready = fetch_json(f"{BASE_URL}/ready")
        status2, seeded = fetch_json(f"{BASE_URL}/demo/seed", method="POST")
        status3, threads = fetch_json(f"{BASE_URL}/threads")
        status4, dashboard = fetch_json(f"{BASE_URL}/dashboard")

        summary = {
            "port": PORT,
            "health": {"status": status, "payload": ready},
            "seed": {"status": status2, "payload": seeded},
            "threads_count": len(threads) if isinstance(threads, list) else 0,
            "dashboard": {"status": status4, "payload": dashboard},
        }
        print(json.dumps(summary, indent=2, default=str))
        return 0
    finally:
        if process.poll() is None:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
