from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse

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

HTML_PAGE = Path(__file__).resolve().parent.parent / "static" / "index.html"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    if not HTML_PAGE.exists():
        raise HTTPException(status_code=500, detail="dashboard template not found")
    return HTMLResponse(content=HTML_PAGE.read_text(encoding="utf-8"))


@app.get("/accounts")
def list_accounts() -> list[Account]:
    return [Account(**payload) for payload in store.accounts.values()]


@app.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(account: Account) -> Account:
    store.upsert_account(account.model_dump())
    return account


@app.get("/people")
def list_people() -> list[Person]:
    return [Person(**payload) for payload in store.people.values()]


@app.post("/people", status_code=status.HTTP_201_CREATED)
def create_person(person: Person) -> Person:
    store.upsert_person(person.model_dump())
    return person


@app.get("/threads")
def list_threads() -> list[Thread]:
    return [Thread(**payload) for payload in store.list_threads()]


@app.post("/threads", status_code=status.HTTP_201_CREATED)
def create_thread(request: ThreadCreateRequest) -> Thread:
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
def list_events() -> list[EventRecord]:
    return [EventRecord(**payload) for payload in store.list_events()]


@app.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(request: EventCreateRequest) -> EventRecord:
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
def list_outcomes() -> list[OutcomeRecord]:
    return [OutcomeRecord(**payload) for payload in store.list_outcomes()]


@app.post("/outcomes", status_code=status.HTTP_201_CREATED)
def create_outcome(request: OutcomeCreateRequest) -> OutcomeRecord:
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
def get_thread(thread_id: str) -> Thread:
    if thread_id not in store.threads:
        raise HTTPException(status_code=404, detail="thread not found")
    return Thread(**store.threads[thread_id])


@app.get("/threads/{thread_id}/events")
def get_thread_events(thread_id: str) -> list[dict[str, Any]]:
    events = [payload for payload in store.list_events() if payload["thread_id"] == thread_id]
    return events


@app.get("/dashboard")
def dashboard() -> dict[str, Any]:
    return workflow_engine.compile_dashboard()


@app.get("/orchestration/{thread_id}")
def get_orchestration(thread_id: str) -> dict[str, Any]:
    return orchestrator.build_flow(thread_id)
