"""Privacy-preserving exports for pilot operational proof."""

from __future__ import annotations

import hashlib
import re
from typing import Any


EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def anonymize(value: Any) -> Any:
    if isinstance(value, str):
        return EMAIL.sub(lambda match: f"contact-{hashlib.sha256(match.group(0).lower().encode()).hexdigest()[:10]}", value)
    if isinstance(value, list):
        return [anonymize(item) for item in value]
    if isinstance(value, dict):
        return {key: anonymize(item) for key, item in value.items() if key not in {"password_hash", "token", "authorization"}}
    return value


def audit_proof(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "occurred_at": event["occurred_at"],
            "event_type": event["event_type"],
            "entity_type": event["entity_type"],
            "entity_id": str(event["entity_id"]),
            "details": anonymize(event["details"]),
        }
        for event in events
    ]
