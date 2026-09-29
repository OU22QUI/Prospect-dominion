from datetime import datetime, timedelta, timezone

import pytest

from app.scoring import score_account, validate_rules


RULES = {"version": 1, "base_score": 10, "rules": [{"signal_type": "intent.pricing", "weight": 60, "max_age_days": 30, "source_trust": 1.0}, {"signal_type": "negative", "weight": -25, "max_age_days": 30}]}


def test_score_is_deterministic_and_explained() -> None:
    now = datetime(2026, 1, 31, tzinfo=timezone.utc)
    events = [{"event_id": "evt-1", "event_type": "intent.pricing", "source": "csv", "occurred_at": now - timedelta(days=15)}]
    result = score_account(events, RULES, now)
    assert result["score"] == 40.0
    assert result["action_type"] == "research"
    assert result["explanation"]["factors"][0]["contribution"] == 30.0


def test_invalid_rules_fail_closed() -> None:
    with pytest.raises(ValueError):
        validate_rules({"version": 2, "rules": []})
