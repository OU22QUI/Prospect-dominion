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
        return {
            "thread_id": thread_id,
            "pipeline": self.pipeline,
            "status": "ready",
            "current_stage": self.pipeline[0],
        }


orchestrator = ProspectOrchestrator()
