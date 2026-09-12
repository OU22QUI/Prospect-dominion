from __future__ import annotations

from typing import Any


class InMemoryStore:
    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, Any]] = {}
        self.people: dict[str, dict[str, Any]] = {}
        self.threads: dict[str, dict[str, Any]] = {}
        self.events: dict[str, dict[str, Any]] = {}
        self.outcomes: dict[str, dict[str, Any]] = {}

    def upsert_account(self, account: dict[str, Any]) -> dict[str, Any]:
        self.accounts[account["id"]] = account
        return account

    def upsert_person(self, person: dict[str, Any]) -> dict[str, Any]:
        self.people[person["id"]] = person
        return person

    def add_thread(self, thread: dict[str, Any]) -> dict[str, Any]:
        self.threads[thread["thread_id"]] = thread
        return thread

    def add_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self.events[event["event_id"]] = event
        return event

    def add_outcome(self, outcome: dict[str, Any]) -> dict[str, Any]:
        self.outcomes[outcome["outcome_id"]] = outcome
        return outcome

    def list_events(self) -> list[dict[str, Any]]:
        return list(self.events.values())

    def list_outcomes(self) -> list[dict[str, Any]]:
        return list(self.outcomes.values())

    def list_threads(self) -> list[dict[str, Any]]:
        return list(self.threads.values())


store = InMemoryStore()
