from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_PORT = os.getenv("API_PORT", "8010")
BASE_URL = os.getenv("PD_BASE_URL", f"http://127.0.0.1:{API_PORT}")
API_KEY = os.getenv("PD_API_KEY", "dev-local-key")
REQUIRED_SERVICES = {
    "api",
    "caddy",
    "crawl4ai",
    "litellm",
    "mem0",
    "n8n",
    "neo4j",
    "osint",
    "postgres",
    "qdrant",
    "redis",
    "workers",
}
HEALTH_REQUIRED = {"api", "litellm", "osint", "postgres", "redis"}


def run_compose(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "--profile", "core", *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )


def compose_services() -> dict[str, dict[str, object]]:
    result = run_compose("ps", "--all", "--format", "json")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker compose ps failed")
    services: dict[str, dict[str, object]] = {}
    output = result.stdout.strip()
    if not output:
        return services
    try:
        decoded = json.loads(output)
        payloads = decoded if isinstance(decoded, list) else [decoded]
    except json.JSONDecodeError:
        payloads = [json.loads(line) for line in output.splitlines() if line.strip()]
    for payload in payloads:
        services[str(payload.get("Service"))] = payload
    return services


def fetch(
    path: str,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    authenticated: bool = True,
) -> tuple[int, object]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if authenticated:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            content = response.read().decode("utf-8")
            return response.status, json.loads(content) if content else {}
    except HTTPError as exc:
        content = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(content) if content else {}
        except json.JSONDecodeError:
            return exc.code, content
    except URLError as exc:
        raise RuntimeError(f"unreachable {path}: {exc}") from exc


def wait_for_ready(timeout_seconds: int) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            status_code, payload = fetch("/ready")
            if status_code == 200 and isinstance(payload, dict) and payload.get("status") == "ready":
                return payload
        except RuntimeError:
            pass
        time.sleep(2)
    raise RuntimeError(f"API did not become ready at {BASE_URL}")


def verify() -> dict[str, object]:
    services = compose_services()
    missing = sorted(REQUIRED_SERVICES - services.keys())
    if missing:
        raise RuntimeError(f"missing Compose services: {', '.join(missing)}")

    not_running = sorted(
        name for name in REQUIRED_SERVICES if str(services[name].get("State", "")).lower() != "running"
    )
    if not_running:
        raise RuntimeError(f"services not running: {', '.join(not_running)}")

    unhealthy = sorted(
        name
        for name in HEALTH_REQUIRED
        if str(services[name].get("Health", "")).lower() not in {"healthy", ""}
    )
    if unhealthy:
        raise RuntimeError(f"services unhealthy: {', '.join(unhealthy)}")

    ready = wait_for_ready(60)
    health_status, health = fetch("/health")
    unauthenticated_status, _ = fetch("/dashboard", method="GET", authenticated=False)
    branding_status, branding = fetch("/branding")
    seed_status, seed = fetch("/demo/seed", method="POST")
    thread_status, thread = fetch(
        "/threads",
        method="POST",
        payload={"person_id": "verify-person", "account_id": "verify-account", "campaign_id": "verify-campaign"},
    )

    if health_status != 200 or not isinstance(health, dict) or health.get("status") != "ok":
        raise RuntimeError("/health verification failed")
    if unauthenticated_status != 401:
        raise RuntimeError(f"unauthorized dashboard access returned {unauthenticated_status}")
    if branding_status != 200:
        raise RuntimeError("/branding verification failed")
    if seed_status != 200:
        raise RuntimeError("demo seed verification failed")
    if thread_status != 201 or not isinstance(thread, dict):
        raise RuntimeError("thread creation verification failed")

    thread_id = str(thread["thread_id"])
    advance_status, advanced = fetch(
        f"/threads/{thread_id}/advance",
        method="POST",
        payload={"event_type": "reply.positive", "source": "deployment-verification"},
    )
    if advance_status != 200:
        raise RuntimeError("workflow advancement verification failed")

    return {
        "status": "passed",
        "base_url": BASE_URL,
        "services": sorted(REQUIRED_SERVICES),
        "ready": ready,
        "health": health,
        "branding": branding,
        "seed": seed,
        "workflow": advanced,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the running Prospect Dominion Compose deployment")
    parser.add_argument("--teardown", action="store_true", help="stop the Compose core profile after verification")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(), indent=2, default=str))
        return 0
    except (RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    finally:
        if args.teardown:
            result = run_compose("down", "--remove-orphans")
            if result.returncode != 0:
                print(result.stderr, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())