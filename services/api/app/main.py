from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    httpx = None

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    redis = None

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models import (
    Account,
    EventCreateRequest,
    EventRecord,
    OutcomeCreateRequest,
    OutcomeRecord,
    Person,
    Thread,
    ThreadCreateRequest,
)
from app.orchestration import orchestrator
from app.stores import store
from app.workflow import workflow_engine

app = FastAPI(title="Prospect Dominion API")
security = HTTPBearer(auto_error=False)

HTML_PAGE = Path(__file__).resolve().parent.parent / "static" / "index.html"
DEFAULT_RUNTIME_PORT = 8000


def get_branding_config() -> dict[str, str]:
    return {
        "brand_name": os.getenv("PD_BRAND_NAME", "Prospect Dominion").strip() or "Prospect Dominion",
        "brand_tagline": os.getenv("PD_BRAND_TAGLINE", "Operational control surface").strip() or "Operational control surface",
        "primary_color": os.getenv("PD_PRIMARY_COLOR", "#4f8ef7").strip() or "#4f8ef7",
    }


def render_dashboard_html() -> str:
    template = HTML_PAGE.read_text(encoding="utf-8")
    branding = get_branding_config()
    replacements = {
        "{{BRAND_NAME}}": branding["brand_name"],
        "{{BRAND_TAGLINE}}": branding["brand_tagline"],
        "{{BRAND_PRIMARY_COLOR}}": branding["primary_color"],
    }
    rendered = template
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered


def get_expected_api_key() -> str:
    key = os.getenv("PD_API_KEY")
    if os.getenv("APP_ENV", "local").strip().lower() == "production":
        if not key or not str(key).strip():
            raise RuntimeError("PD_API_KEY is required in production mode")
        if not str(key).startswith("prod-"):
            raise RuntimeError("PD_API_KEY must start with 'prod-' in production mode")
        return str(key)
    return key or "dev-local-key"


def get_default_role() -> str:
    return os.getenv("PD_DEFAULT_ROLE", "admin").strip().lower()


def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    expected_api_key = get_expected_api_key()
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    if credentials.credentials != expected_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return credentials.credentials


def require_role(*allowed_roles: str):
    def dependency(request: Request, api_key: str = Depends(require_api_key)) -> str:
        requested_role = (request.headers.get("X-Role") or get_default_role()).strip().lower()
        if not allowed_roles:
            return requested_role
        if requested_role not in {role.lower() for role in allowed_roles}:
            raise HTTPException(status_code=403, detail=f"Role '{requested_role}' is not allowed for this action")
        return requested_role

    return dependency


def resolve_runtime_port(default_port: int = DEFAULT_RUNTIME_PORT) -> int:
    requested = os.getenv("PD_PORT")
    candidates: list[int] = []

    def normalize(value: int) -> int:
        if not 1 <= value <= 65535:
            return DEFAULT_RUNTIME_PORT
        return value

    if requested:
        try:
            candidates.append(normalize(int(requested)))
        except ValueError:
            candidates.append(normalize(default_port))

    start_port = normalize(default_port)
    for offset in range(25):
        port = start_port + offset
        if port > 65535:
            port = 1 + (port - 65535 - 1)
        candidates.append(port)

    seen: set[int] = set()
    for port in candidates:
        if port in seen:
            continue
        seen.add(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue

    raise RuntimeError(f"No free local port found starting at {default_port}")


def validate_runtime_config() -> dict[str, Any]:
    issues: list[str] = []
    app_env = os.getenv("APP_ENV", "local").strip().lower()
    required = ["PD_API_KEY"]

    if app_env == "production":
        required.extend(["JWT_SECRET", "PUBLIC_BASE_URL"])

    for key in required:
        value = os.getenv(key)
        if value is None or not str(value).strip():
            issues.append(key)

    if app_env == "production" and not os.getenv("PD_API_KEY", "").startswith("prod-"):
        issues.append("PD_API_KEY_PATTERN")

    if app_env != "production":
        return {
            "status": "valid",
            "environment": app_env,
            "issues": [],
            "required": required,
        }

    return {
        "status": "valid" if not issues else "invalid",
        "environment": app_env,
        "issues": issues,
        "required": required,
    }


def _readiness_checks() -> dict[str, Any]:
    checks: dict[str, Any] = {
        "api": {"status": "ok"},
        "database": {"status": "ok"},
        "qdrant": {"status": "unknown"},
        "redis": {"status": "unknown"},
    }

    db_path = store.db_path
    checks["database"] = {"status": "ok" if db_path.exists() else "missing", "path": str(db_path)}

    qdrant_url = os.getenv("QDRANT_URL", "http://127.0.0.1:6335")
    if httpx is None:
        checks["qdrant"] = {"status": "unknown", "url": qdrant_url, "note": "httpx not installed"}
    else:
        try:
            response = httpx.get(f"{qdrant_url}/readyz", timeout=3.0)
            checks["qdrant"] = {
                "status": "ok" if response.status_code == 200 else "degraded",
                "url": qdrant_url,
                "http_status": response.status_code,
            }
        except Exception as exc:  # pragma: no cover - runtime dependency check
            checks["qdrant"] = {"status": "unavailable", "url": qdrant_url, "error": str(exc)}

    redis_url = os.getenv("REDIS_URL", "redis://:change-me-strong@127.0.0.1:6380")
    if redis is None:
        checks["redis"] = {"status": "unknown", "url": redis_url, "note": "redis package not installed"}
    else:
        try:
            client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            checks["redis"] = {"status": "ok", "url": redis_url}
        except Exception as exc:  # pragma: no cover - runtime dependency check
            checks["redis"] = {"status": "unavailable", "url": redis_url, "error": str(exc)}

    return checks


@app.get("/branding")
def branding() -> dict[str, str]:
    return get_branding_config()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    checks = _readiness_checks()
    config = validate_runtime_config()
    degraded = any(item.get("status") not in {"ok", "unknown"} for item in checks.values())
    if config["status"] == "invalid":
        return {
            "status": "degraded",
            "service": "prospect-dominion-api",
            "checks": checks,
            "config": config,
        }
    return {
        "status": "ready" if not degraded else "degraded",
        "service": "prospect-dominion-api",
        "checks": checks,
        "config": config,
    }


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    if not HTML_PAGE.exists():
        raise HTTPException(status_code=500, detail="dashboard template not found")
    return HTMLResponse(content=render_dashboard_html())


@app.get("/accounts")
def list_accounts(api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> list[Account]:
    return [Account(**payload) for payload in store.accounts.values()]


@app.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(account: Account, api_key: str = Depends(require_role("ops", "admin"))) -> Account:
    store.upsert_account(account.model_dump())
    return account


@app.get("/people")
def list_people(api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> list[Person]:
    return [Person(**payload) for payload in store.people.values()]


@app.post("/people", status_code=status.HTTP_201_CREATED)
def create_person(person: Person, api_key: str = Depends(require_role("ops", "admin"))) -> Person:
    store.upsert_person(person.model_dump())
    return person


@app.get("/threads")
def list_threads(api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> list[Thread]:
    return [Thread(**payload) for payload in store.list_threads()]


@app.post("/threads", status_code=status.HTTP_201_CREATED)
def create_thread(request: ThreadCreateRequest, api_key: str = Depends(require_role("ops", "admin"))) -> Thread:
    thread = Thread(
        thread_id=f"thread_{len(store.threads) + 1}",
        person_id=request.person_id,
        account_id=request.account_id,
        campaign_id=request.campaign_id,
        opp_stage=request.opp_stage,
        consent_basis=request.consent_basis,
        next_action_at=request.next_action_at,
    )
    store.add_thread(thread.model_dump())
    return thread


@app.get("/events")
def list_events(api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> list[EventRecord]:
    return [EventRecord(**payload) for payload in store.list_events()]


@app.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(request: EventCreateRequest, api_key: str = Depends(require_role("ops", "admin"))) -> EventRecord:
    event = EventRecord(
        event_id=f"event_{len(store.events) + 1}",
        thread_id=request.thread_id,
        event_type=request.event_type,
        source=request.source,
        payload=request.payload,
    )
    store.add_event(event.model_dump())
    return event


@app.get("/outcomes")
def list_outcomes(api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> list[OutcomeRecord]:
    return [OutcomeRecord(**payload) for payload in store.list_outcomes()]


@app.post("/outcomes", status_code=status.HTTP_201_CREATED)
def create_outcome(request: OutcomeCreateRequest, api_key: str = Depends(require_role("ops", "admin"))) -> OutcomeRecord:
    outcome = OutcomeRecord(
        outcome_id=f"outcome_{len(store.outcomes) + 1}",
        thread_id=request.thread_id,
        account_id=request.account_id,
        stage_from=request.stage_from,
        stage_to=request.stage_to,
        reason=request.reason,
        value_amount=request.value_amount,
        attributed_signal=request.attributed_signal,
    )
    store.add_outcome(outcome.model_dump())
    return outcome


@app.get("/threads/{thread_id}")
def get_thread(thread_id: str, api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> Thread:
    if thread_id not in store.threads:
        raise HTTPException(status_code=404, detail="thread not found")
    return Thread(**store.threads[thread_id])


@app.get("/threads/{thread_id}/events")
def get_thread_events(thread_id: str, api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> list[dict[str, Any]]:
    events = [payload for payload in store.list_events() if payload["thread_id"] == thread_id]
    return events


@app.get("/dashboard")
def dashboard(api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> dict[str, Any]:
    return workflow_engine.compile_dashboard()


@app.get("/orchestration/{thread_id}")
def get_orchestration(thread_id: str, api_key: str = Depends(require_role("viewer", "ops", "admin"))) -> dict[str, Any]:
    return orchestrator.build_flow(thread_id)


@app.post("/threads/{thread_id}/advance")
def advance_thread(thread_id: str, payload: dict[str, Any], api_key: str = Depends(require_role("ops", "admin"))) -> dict[str, Any]:
    if thread_id not in store.threads:
        raise HTTPException(status_code=404, detail="thread not found")

    event_type = payload.get("event_type") or "reply.positive"
    result = orchestrator.advance(thread_id, event_type)
    return result


@app.post("/threads/{thread_id}/events")
def record_thread_event(thread_id: str, payload: dict[str, Any], api_key: str = Depends(require_role("ops", "admin"))) -> dict[str, Any]:
    if thread_id not in store.threads:
        raise HTTPException(status_code=404, detail="thread not found")

    event = EventRecord(
        event_id=f"event_{len(store.events) + 1}",
        thread_id=thread_id,
        event_type=payload.get("event_type", "reply.positive"),
        source=payload.get("source", "demo"),
        payload=payload.get("payload", {}),
    )
    store.add_event(event.model_dump())

    thread_state = orchestrator.advance(thread_id, event.event_type)
    return {
        "thread_id": thread_id,
        "event": event.model_dump(),
        "thread_state": thread_state,
    }


@app.post("/demo/seed")
def seed_demo() -> dict[str, Any]:
    account = Account(
        id="acct-demo-1",
        domain="acme.example",
        legal_name="Acme Corp",
        display_name="Acme",
        industry="SaaS",
        icp_score=0.82,
        enrichment={"segment": "mid-market-b2b", "priority": "high"},
    )
    if account.id not in store.accounts:
        store.upsert_account(account.model_dump())

    person = Person(
        id="person-demo-1",
        account_id=account.id,
        full_name="Dana Hughes",
        title="VP Sales",
        seniority="VP",
        role_function="sales",
        linkedin_url="https://example.com/dana",
        psychographics={"persona": "VP of sales", "buying_signals": ["expansion", "ops pressure"]},
    )
    if person.id not in store.people:
        store.upsert_person(person.model_dump())

    thread_id = "thread_demo_1"
    if thread_id not in store.threads:
        thread = Thread(
            thread_id=thread_id,
            person_id=person.id,
            account_id=account.id,
            campaign_id="campaign_demo_1",
            opp_stage="engaged",
            consent_basis="consent",
        )
        store.add_thread(thread.model_dump())

    event = EventRecord(
        event_id="event_demo_1",
        thread_id=thread_id,
        event_type="lead.discovered",
        source="wg2",
        payload={"channel": "signal", "source_name": "demo"},
    )
    if event.event_id not in store.events:
        store.add_event(event.model_dump())

    outcome = OutcomeRecord(
        outcome_id="outcome_demo_1",
        thread_id=thread_id,
        account_id=account.id,
        stage_from="engaged",
        stage_to="meeting_booked",
        reason="demo workflow seeded",
        value_amount=15000.0,
        attributed_signal="signal.demo",
    )
    if outcome.outcome_id not in store.outcomes:
        store.add_outcome(outcome.model_dump())

    return {
        "seeded": True,
        "account_id": account.id,
        "person_id": person.id,
        "thread_id": thread_id,
        "event_id": event.event_id,
        "outcome_id": outcome.outcome_id,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=resolve_runtime_port())
