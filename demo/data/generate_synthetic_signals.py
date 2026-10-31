from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


OUTPUT = Path(__file__).with_name("synthetic_signals.csv")

VALID_DOMAINS = [
    "example.test",
    "northstar.example.test",
    "atlas.example.test",
    "harbor.example.test",
    "spark.example.test",
]

FULL_NAMES = [
    "Ava Shah",
    "Milo Chen",
    "Emma Lopez",
    "Theo Nguyen",
    "Noah Patel",
    "Sofia Alvarez",
    "Leo Martin",
    "Ruby Walker",
    "Daniel Brooks",
    "Iris Kim",
]

SIGNAL_TYPES = [
    "company_profile",
    "engagement_signal",
    "trigger_event",
    "intent_signal",
]

CONSENT_BASES = ["consent", "legitimate_interest", "none"]


def main() -> None:
    now = datetime.now(timezone.utc)
    rows = []
    for idx in range(1, 11):
        domain = VALID_DOMAINS[idx % len(VALID_DOMAINS)]
        full_name = FULL_NAMES[(idx - 1) % len(FULL_NAMES)]
        email = f"{full_name.split()[0].lower()}{idx}@{domain}"
        signal_type = SIGNAL_TYPES[(idx - 1) % len(SIGNAL_TYPES)]
        consent = CONSENT_BASES[(idx - 1) % len(CONSENT_BASES)]
        observed_at = (now - timedelta(days=idx * 2, hours=idx)).isoformat()
        rows.append(
            {
                "external_id": f"acct-{idx:03d}",
                "domain": domain,
                "email": email,
                "full_name": full_name,
                "signal_type": signal_type,
                "observed_at": observed_at,
                "consent_basis": consent,
            }
        )

    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "external_id",
                "domain",
                "email",
                "full_name",
                "signal_type",
                "observed_at",
                "consent_basis",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} synthetic rows to {OUTPUT}")


if __name__ == "__main__":
    main()
