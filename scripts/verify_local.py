from __future__ import annotations

import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = os.getenv("PD_BASE_URL", "http://127.0.0.1:8010")
API_KEY = os.getenv("PD_API_KEY", "dev-local-key")


def fetch(url: str):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            return exc.code, json.loads(body) if body else {}
        except Exception:
            return exc.code, {}
    except URLError as exc:
        raise RuntimeError(f"unreachable: {url} :: {exc}") from exc


def main() -> int:
    for attempt in range(1, 31):
        try:
            status, payload = fetch(f"{BASE_URL}/ready")
            if status == 200:
                print(json.dumps({"attempt": attempt, "status": status, "payload": payload}, indent=2))
                if payload.get("status") == "ready":
                    return 0
        except RuntimeError as exc:
            print(f"attempt {attempt}: {exc}")
        time.sleep(2)

    print(f"service at {BASE_URL} did not become ready in time")
    return 1


if __name__ == "__main__":
    sys.exit(main())
