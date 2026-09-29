"""Deterministic, explainable account scoring for the pilot workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ACTION_THRESHOLDS = ((80, "draft_outreach", 0.9), (55, "request_intro", 0.75), (25, "research", 0.6))


def validate_rules(rules: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(rules, dict) or rules.get("version") != 1:
        raise ValueError("icp_rules must be an object with version 1")
    base = rules.get("base_score", 0)
    entries = rules.get("rules", [])
    if not isinstance(base, (int, float)) or not isinstance(entries, list):
        raise ValueError("base_score must be numeric and rules must be a list")
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("signal_type"), str) or not isinstance(entry.get("weight"), (int, float)):
            raise ValueError("each rule requires signal_type and numeric weight")
        max_age_days = entry.get("max_age_days", 30)
        if not isinstance(max_age_days, (int, float)) or max_age_days <= 0:
            raise ValueError("max_age_days must be positive")
        normalized.append({"signal_type": entry["signal_type"], "weight": float(entry["weight"]), "max_age_days": float(max_age_days), "source_trust": float(entry.get("source_trust", 1.0))})
    return {"version": 1, "base_score": float(base), "rules": normalized}


def score_account(events: list[dict[str, Any]], rules: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    config = validate_rules(rules)
    current = now or datetime.now(timezone.utc)
    score = config["base_score"]
    factors: list[dict[str, Any]] = []
    for event in events:
        event_type = event["event_type"]
        occurred_at = event["occurred_at"]
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (current - occurred_at).total_seconds() / 86400)
        for rule in config["rules"]:
            if rule["signal_type"] != event_type:
                continue
            freshness = max(0.0, 1.0 - age_days / rule["max_age_days"])
            contribution = round(rule["weight"] * freshness * rule["source_trust"], 3)
            score += contribution
            factors.append({"event_id": event.get("event_id"), "signal_type": event_type, "age_days": round(age_days, 2), "freshness": round(freshness, 3), "contribution": contribution, "source": event.get("source")})
    bounded = round(max(0.0, min(100.0, score)), 3)
    action, confidence = "wait", 0.5
    for threshold, candidate, candidate_confidence in ACTION_THRESHOLDS:
        if bounded >= threshold:
            action, confidence = candidate, candidate_confidence
            break
    return {"score": bounded, "explanation": {"base_score": config["base_score"], "factors": factors, "rule_version": 1}, "action_type": action, "confidence": confidence}
