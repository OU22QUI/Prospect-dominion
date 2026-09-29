import pytest

from app.csv_connector import parse_signals


CONTENT = "external_id,domain,email,full_name,signal_type,observed_at\nabc,acme.test,dana@acme.test,Dana Hughes,intent.pricing,2026-01-01T12:00:00Z\n"


def test_csv_connector_parses_provenance_and_is_deterministic() -> None:
    rows, cursor = parse_signals(CONTENT)
    repeat_rows, repeat_cursor = parse_signals(CONTENT)
    assert rows[0]["external_id"] == "abc"
    assert rows[0]["line_number"] == 2
    assert rows[0]["idempotency_key"] == repeat_rows[0]["idempotency_key"]
    assert cursor == repeat_cursor


def test_csv_connector_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        parse_signals("email\na@acme.test\n")


def test_csv_connector_rejects_unknown_legal_basis() -> None:
    invalid = CONTENT.replace("observed_at\n", "observed_at,consent_basis\n").replace("Z\n", "Z,unknown\n")
    with pytest.raises(ValueError, match="consent_basis"):
        parse_signals(invalid)


def test_csv_connector_defaults_missing_consent_basis_to_none() -> None:
    rows, _ = parse_signals(CONTENT)
    assert rows[0]["consent_basis"] == "none"


def test_csv_connector_distinguishes_signals_for_different_accounts() -> None:
    content = (
        "external_id,domain,email,full_name,signal_type,observed_at\n"
        "shared,acme.test,dana@acme.test,Dana,intent.pricing,2026-01-01T12:00:00Z\n"
        "shared,other.test,lee@other.test,Lee,intent.pricing,2026-01-01T12:00:00Z\n"
    )
    rows, _ = parse_signals(content)
    assert rows[0]["idempotency_key"] != rows[1]["idempotency_key"]
