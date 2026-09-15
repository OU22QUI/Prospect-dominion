from __future__ import annotations

from typing import Any


class ProspectOrchestrator:
    def __init__(self) -> None:
        self.pipeline = [
            "lead.discovered",
            "lead.enriched",
            "lead.scored",
            "touch.planned",
            "touch.sent",
            "reply.classified",
            "reply.positive",
            "meeting.booked",
            "outcome.logged",
        ]

    def build_flow(self, thread_id: str) -> dict[str, Any]:
        state = self.get_state(thread_id)
        return {
            "thread_id": thread_id,
            "pipeline": self.pipeline,
            "status": "ready",
            "current_stage": state["current_stage"],
            "progress": state["progress"],
        }

    def get_state(self, thread_id: str) -> dict[str, Any]:
        # This starter implementation persists the thread stage in the thread payload itself.
        from app.stores import store

        thread = store.threads.get(thread_id, {})
        current_stage = thread.get("opp_stage") or self.pipeline[0]
        progress = self.pipeline.index(current_stage) + 1 if current_stage in self.pipeline else 0
        return {
            "current_stage": current_stage,
            "progress": min(progress, len(self.pipeline)),
        }

    def advance(self, thread_id: str, event_type: str) -> dict[str, Any]:
        from app.stores import store

        current = self.get_state(thread_id)["current_stage"]
        stage_order = {
            stage: index for index, stage in enumerate(self.pipeline)
        }
        next_stage = current
        if event_type in stage_order:
            next_stage = event_type
        elif current in stage_order:
            next_index = stage_order[current] + 1
            if next_index < len(self.pipeline):
                next_stage = self.pipeline[next_index]

        thread = store.threads.get(thread_id)
        if not thread:
            raise ValueError("thread not found")

        thread["opp_stage"] = next_stage
        thread["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        store.add_thread(thread)

        return {
            "thread_id": thread_id,
            "current_stage": next_stage,
            "progress": min(stage_order.get(next_stage, 0) + 1, len(self.pipeline)),
        }


orchestrator = ProspectOrchestrator()
