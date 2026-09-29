"""Strict CSV connector for the first pilot data source."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from io import StringIO
from typing import Any


REQUIRED_COLUMNS = {"external_id", "domain", "email", "full_name", "signal_type", "observed_at"}
CONSENT_BASES = {"none", "consent", "legitimate_interest"}
MAX_ROWS = 500
MAX_BYTES = 1_000_000


def _clean(value: str | None) -> str:
    return (value or "").strip()


def parse_signals(content: str) -> tuple[list[dict[str, Any]], str]:
    if len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV exceeds the 1 MB pilot upload limit")
    reader = csv.DictReader(StringIO(content))
    fields = set(reader.fieldnames or [])
    missing = REQUIRED_COLUMNS - fields
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(reader, start=2):
        if len(rows) >= MAX_ROWS:
            raise ValueError("CSV exceeds the 500-row pilot import limit")
        try:
            observed_at = datetime.fromisoformat(_clean(raw["observed_at"]).replace("Z", "+00:00"))
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValueError(f"row {line_number}: observed_at must be ISO-8601") from exc
        row = {key: _clean(value) for key, value in raw.items() if key is not None}
        required_values = [row[column] for column in REQUIRED_COLUMNS - {"observed_at"}]
        if not all(required_values) or "@" not in row["email"] or "." not in row["domain"]:
            raise ValueError(f"row {line_number}: required values are invalid")
        consent_basis = row.get("consent_basis", "none").lower()
        if consent_basis not in CONSENT_BASES:
            raise ValueError(f"row {line_number}: consent_basis must be none, consent, or legitimate_interest")
        row["consent_basis"] = consent_basis
        row["observed_at"] = observed_at
        row["line_number"] = line_number
        identity = json.dumps(
            (row["domain"].lower(), row["email"].lower(), row["external_id"], row["signal_type"], observed_at.isoformat()),
            separators=(",", ":"),
        )
        row["idempotency_key"] = hashlib.sha256(identity.encode()).hexdigest()
        rows.append(row)
    if not rows:
        raise ValueError("CSV contains no data rows")
    digest = hashlib.sha256(content.encode()).hexdigest()
    return rows, digest
