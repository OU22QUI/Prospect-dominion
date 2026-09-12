from __future__ import annotations

from typing import Any

from app.stores import store


class WorkflowEngine:
    def __init__(self) -> None:
        self._state = {"events": [], "outcomes": []}

    def ingest_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self._state["events"].append(event)
        return event

    def compile_dashboard(self) -> dict[str, Any]:
        threads = list(store.list_threads())
        events = store.list_events()
        outcomes = store.list_outcomes()

        return {
            "thread_count": len(threads),
            "event_count": len(events),
            "outcome_count": len(outcomes),
            "threads": [
                {
                    "thread_id": thread["thread_id"],
                    "opp_stage": thread["opp_stage"],
                    "person_id": thread["person_id"],
                    "next_action_at": thread.get("next_action_at"),
                }
                for thread in threads
            ],
            "recent_outcomes": outcomes[-5:],
        }


workflow_engine = WorkflowEngine()
