from __future__ import annotations

import base64
import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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

import hashlib
import json
from app.csv_connector import parse_signals
from app.exports import audit_proof
from app.resend import ResendSender, verify_webhook
from app.scoring import score_account, validate_rules
from app.security import hash_password, issue_token, verify_password, verify_token

try:
    from app.pilot_store import PilotStore
except ModuleNotFoundError:  # pragma: no cover
    PilotStore = None

app = FastAPI(title="Prospect Dominion API")
security = HTTPBearer(auto_error=False)

APP_HTML_PAGE = Path(__file__).resolve().parent.parent / "static" / "app.html"

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
    configured_role = os.getenv("PD_DEFAULT_ROLE")
    if configured_role:
        return configured_role.strip().lower()
    return "viewer" if os.getenv("APP_ENV", "local").strip().lower() == "production" else "admin"


def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    expected_api_key = get_expected_api_key()
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    if credentials.credentials != expected_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return credentials.credentials


def require_role(*allowed_roles: str):
    def dependency(api_key: str = Depends(require_api_key)) -> str:
        requested_role = get_default_role()
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
        required.extend([
            "JWT_SECRET",
            "PUBLIC_BASE_URL",
            "PG_DSN",
            "PD_STORE_BACKEND",
            "PD_PUBLIC_HOST",
            "PD_CADDYFILE",
            "PD_DEFAULT_ROLE",
            "RESEND_API_KEY",
            "RESEND_WEBHOOK_SECRET",
        ])

    for key in required:
        value = os.getenv(key)
        if value is None or not str(value).strip():
            issues.append(key)

    if app_env == "production" and not os.getenv("PD_API_KEY", "").startswith("prod-"):
        issues.append("PD_API_KEY_PATTERN")
    if app_env == "production":
        jwt_secret = os.getenv("JWT_SECRET", "")
        if len(jwt_secret) < 32 or jwt_secret.strip().lower() in {"change-me", "changeme", "secret"}:
            issues.append("JWT_SECRET_STRENGTH")
        if not os.getenv("PUBLIC_BASE_URL", "").startswith("https://"):
            issues.append("PUBLIC_BASE_URL_HTTPS")
        if os.getenv("PD_STORE_BACKEND", "").strip().lower() != "postgres":
            issues.append("PD_STORE_BACKEND_POSTGRES")
        public_host = os.getenv("PD_PUBLIC_HOST", "").strip().lower()
        if public_host != (urlparse(os.getenv("PUBLIC_BASE_URL", "")).hostname or "").lower():
            issues.append("PD_PUBLIC_HOST_MISMATCH")
        if Path(os.getenv("PD_CADDYFILE", "").replace("\\", "/")).name != "Caddyfile.production":
            issues.append("PD_CADDYFILE_PRODUCTION")
        if get_default_role() != "viewer":
            issues.append("PD_DEFAULT_ROLE_LEGACY_VIEWER_ONLY")
        resend_api_key = os.getenv("RESEND_API_KEY", "")
        if not resend_api_key.startswith("re_") or resend_api_key.startswith("re_example"):
            issues.append("RESEND_API_KEY_PATTERN")
        webhook_secret = os.getenv("RESEND_WEBHOOK_SECRET", "")
        try:
            encoded_secret = webhook_secret.removeprefix("whsec_")
            decoded_secret = base64.b64decode(encoded_secret + "=" * (-len(encoded_secret) % 4), validate=True)
        except ValueError:
            decoded_secret = b""
        if not webhook_secret.startswith("whsec_") or len(decoded_secret) != 32:
            issues.append("RESEND_WEBHOOK_SECRET_PATTERN")

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

    if os.getenv("PD_STORE_BACKEND", "sqlite").strip().lower() == "postgres":
        try:
            with get_pilot_store().transaction() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = {"status": "ok", "backend": "postgres"}
        except Exception as exc:
            checks["database"] = {"status": "unavailable", "backend": "postgres", "error": type(exc).__name__}
    else:
        db_path = store.db_path
        checks["database"] = {"status": "ok" if db_path.exists() else "missing", "backend": "sqlite", "path": str(db_path)}

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
    app_env = config["environment"]
    degraded = any(item.get("status") not in {"ok", "unknown"} for item in checks.values())
    if app_env != "production":
        degraded = any(checks[name].get("status") not in {"ok", "unknown"} for name in ("api", "database"))
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


# ==============================================================================
# Pilot /v1 Governed API & Operator Console
# ==============================================================================


def get_pilot_store() -> PilotStore:
    if PilotStore is None:
        raise HTTPException(status_code=500, detail="Pilot store dependencies not installed")
    try:
        return PilotStore()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def require_pilot_auth(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")
    try:
        payload = verify_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    store_instance = get_pilot_store()
    principal = store_instance.principal(payload["sub"], payload["tenant"])
    if not principal:
        raise HTTPException(status_code=401, detail="User or workspace not found")
    return principal


def require_pilot_role(*allowed_roles: str):
    def dependency(principal: dict[str, Any] = Depends(require_pilot_auth)) -> dict[str, Any]:
        if allowed_roles and principal.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return principal
    return dependency


@app.get("/app", response_class=HTMLResponse)
def get_operator_app() -> str:
    if not APP_HTML_PAGE.is_file():
        raise HTTPException(status_code=404, detail="Operator app not found")
    return APP_HTML_PAGE.read_text(encoding="utf-8")


@app.post("/v1/auth/bootstrap", status_code=201)
def pilot_bootstrap(payload: dict[str, Any]) -> dict[str, Any]:
    store_instance = get_pilot_store()
    try:
        p_hash = hash_password(str(payload["password"]))
        res = store_instance.bootstrap(
            tenant_slug=str(payload["tenant_slug"]),
            tenant_name=str(payload["tenant_name"]),
            email=str(payload["email"]),
            display_name=str(payload["display_name"]),
            password_hash=p_hash,
        )
        token = issue_token(user_id=res["user_id"], tenant_id=res["tenant_id"])
        return {**res, "token": token}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/v1/auth/login")
def pilot_login(payload: dict[str, Any]) -> dict[str, Any]:
    store_instance = get_pilot_store()
    user = store_instance.authenticate(str(payload.get("email", "")))
    if not user or not verify_password(str(payload.get("password", "")), user.get("password_hash")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = issue_token(user_id=str(user["user_id"]), tenant_id=str(user["tenant_id"]))
    return {
        "token": token,
        "role": user["role"],
        "user": {
            "user_id": str(user["user_id"]),
            "tenant_id": str(user["tenant_id"]),
            "role": user["role"],
        },
    }


@app.get("/v1/me")
def pilot_me(principal: dict[str, Any] = Depends(require_pilot_auth)) -> dict[str, Any]:
    return principal


@app.post("/v1/users", status_code=201)
def pilot_create_user(
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    try:
        p_hash = hash_password(str(payload["password"]))
        user = store_instance.create_user(
            tenant_id=principal["tenant_id"],
            actor_id=str(principal["user_id"]),
            email=str(payload["email"]),
            display_name=str(payload["display_name"]),
            password_hash=p_hash,
            role=str(payload["role"]),
        )
        return user
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/v1/users")
def pilot_list_users(principal: dict[str, Any] = Depends(require_pilot_auth)) -> dict[str, Any]:
    store_instance = get_pilot_store()
    return {"items": store_instance.list_users(principal["tenant_id"])}


@app.post("/v1/sources/csv/import")
def pilot_import_csv(
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    content = str(payload.get("content", ""))
    source_name = str(payload.get("source_name", "csv"))
    try:
        rows, digest = parse_signals(content)
    except ValueError as exc:
        import_key = hashlib.sha256(content.encode()).hexdigest()[:32]
        store_instance.record_csv_failure(principal["tenant_id"], str(principal["user_id"]), source_name, import_key, str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    return store_instance.import_csv_signals(principal["tenant_id"], str(principal["user_id"]), source_name, rows, digest)


@app.get("/v1/settings/icp-rules")
def pilot_get_rules(principal: dict[str, Any] = Depends(require_pilot_auth)) -> dict[str, Any]:
    store_instance = get_pilot_store()
    settings = store_instance.get_settings(principal["tenant_id"])
    return settings.get("icp_rules", {})


@app.put("/v1/settings/icp-rules")
def pilot_save_rules(
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    try:
        rules = validate_rules(payload.get("rules", {}))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return store_instance.save_rules(principal["tenant_id"], str(principal["user_id"]), rules)


@app.post("/v1/accounts/{account_id}/score")
def pilot_score_account(
    account_id: str,
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    settings = store_instance.get_settings(principal["tenant_id"])
    events = store_instance.events_for_account(principal["tenant_id"], account_id)
    score_res = score_account(events, settings.get("icp_rules", {}))
    return store_instance.save_score(principal["tenant_id"], str(principal["user_id"]), account_id, score_res)


@app.get("/v1/priority-queue")
def pilot_priority_queue(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.priority_queue(principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.post("/v1/approvals", status_code=201)
def pilot_create_approval(
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    return store_instance.request_approval(principal["tenant_id"], str(principal["user_id"]), payload)


@app.post("/v1/approvals/{approval_id}/approve")
def pilot_approve(
    approval_id: str,
    payload: dict[str, Any] | None = None,
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    reason = (payload or {}).get("reason") if isinstance(payload, dict) else None
    approval = store_instance.decide_approval(principal["tenant_id"], str(principal["user_id"]), approval_id, "approved", reason)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found, expired, or already decided")
    return approval


@app.post("/v1/approvals/{approval_id}/reject")
def pilot_reject(
    approval_id: str,
    payload: dict[str, Any] | None = None,
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    reason = (payload or {}).get("reason") if isinstance(payload, dict) else None
    approval = store_instance.decide_approval(principal["tenant_id"], str(principal["user_id"]), approval_id, "rejected", reason)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found, expired, or already decided")
    return approval


@app.post("/v1/approvals/{approval_id}/send")
def pilot_send(
    approval_id: str,
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    idempotency_key = str(payload.get("idempotency_key", ""))
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="idempotency_key is required")
    try:
        claim = store_instance.claim_approved_send(
            tenant_id=principal["tenant_id"],
            actor_id=str(principal["user_id"]),
            approval_id=approval_id,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if not claim["should_send"]:
        return {"attempt": claim["attempt"], "sent": False}

    sender = ResendSender()
    try:
        msg_id = sender.send(claim["payload"])
        attempt = store_instance.record_send_result(
            tenant_id=principal["tenant_id"],
            actor_id=str(principal["user_id"]),
            attempt_id=str(claim["attempt"]["id"]),
            message_id=msg_id,
        )
        return {"attempt": attempt, "sent": True}
    except Exception as exc:
        attempt = store_instance.record_send_result(
            tenant_id=principal["tenant_id"],
            actor_id=str(principal["user_id"]),
            attempt_id=str(claim["attempt"]["id"]),
            error=str(exc),
        )
        return {"attempt": attempt, "sent": False, "error": str(exc)}


@app.post("/v1/webhooks/resend/{tenant_id}")
async def pilot_resend_webhook(
    tenant_id: str,
    request: Request,
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    if tenant_id != store_instance.bootstrap_tenant_id():
        raise HTTPException(status_code=404, detail="Webhook not found")
    raw_body = await request.body()
    try:
        verify_webhook(raw_body, dict(request.headers))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        event = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    processed = store_instance.receive_resend_webhook(tenant_id, event)
    return {"processed": processed}


# List endpoints
@app.get("/v1/accounts")
def pilot_list_accounts(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("accounts", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.post("/v1/accounts", status_code=201)
def pilot_create_account(
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    return store_instance.create_account(principal["tenant_id"], str(principal["user_id"]), payload)


@app.get("/v1/people")
def pilot_list_people(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("people", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.post("/v1/people", status_code=201)
def pilot_create_person(
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    return store_instance.create_person(principal["tenant_id"], str(principal["user_id"]), payload)


@app.get("/v1/threads")
def pilot_list_threads(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("threads", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.post("/v1/threads", status_code=201)
def pilot_create_thread(
    payload: dict[str, Any],
    principal: dict[str, Any] = Depends(require_pilot_role("owner", "operator")),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    return store_instance.create_thread(principal["tenant_id"], str(principal["user_id"]), payload)


@app.get("/v1/events")
def pilot_list_events(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("events", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/v1/outcomes")
def pilot_list_outcomes(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("outcomes", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/v1/approvals")
def pilot_list_approvals(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("approvals", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/v1/source-connections")
def pilot_list_sources(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("source_connections", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/v1/ingest-failures")
def pilot_list_ingest_failures(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("ingest_failures", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/v1/action-feedback")
def pilot_list_action_feedback(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("action_feedback", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/v1/audit-events")
def pilot_list_audit_events(
    limit: int = 50,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_pilot_auth),
) -> dict[str, Any]:
    store_instance = get_pilot_store()
    items, total = store_instance.list_records("audit_events", principal["tenant_id"], limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.get("/v1/exports/audit-proof")
def pilot_audit_proof(principal: dict[str, Any] = Depends(require_pilot_auth)) -> list[dict[str, Any]]:
    store_instance = get_pilot_store()
    events, _ = store_instance.list_records("audit_events", principal["tenant_id"], limit=1000, offset=0)
    return audit_proof(events)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=resolve_runtime_port())
