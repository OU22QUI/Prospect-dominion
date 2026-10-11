import pytest

from scripts import backup_restore_rehearsal
from scripts.backup_restore_rehearsal import validate_restore_database


@pytest.mark.parametrize(
    "database",
    [
        "prospect_dominion",
        "pilot_customer",
        "pd_restore_",
        "pd_restore_user-database",
        "pd_restore_' OR 1=1 --",
        f"pd_restore_{'x' * 51}",
    ],
)
def test_restore_database_name_must_be_isolated_and_safe(database: str) -> None:
    with pytest.raises(ValueError, match="pd_restore_ prefix"):
        validate_restore_database(database)


def test_restore_database_name_accepts_isolated_identifier() -> None:
    validate_restore_database("pd_restore_test_123")


def test_invalid_restore_database_stops_before_compose(monkeypatch, capsys) -> None:
    monkeypatch.setenv("PD_RESTORE_TEST_DB", "prospect_dominion")
    monkeypatch.setattr(backup_restore_rehearsal, "run", lambda *args, **kwargs: pytest.fail("Compose must not run"))

    assert backup_restore_rehearsal.main() == 2
    assert "pd_restore_" in capsys.readouterr().err


def test_rehearsal_fingerprints_each_table_and_protects_existing_database(monkeypatch) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setenv("PD_RESTORE_TEST_DB", "pd_restore_test")

    def fake_compose(*args: str, **kwargs):
        captured["shell_script"] = args[-1]
        return backup_restore_rehearsal.subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(backup_restore_rehearsal, "run", fake_compose)
    monkeypatch.setattr(
        backup_restore_rehearsal.subprocess,
        "run",
        lambda *args, **kwargs: backup_restore_rehearsal.subprocess.CompletedProcess(args, 0, stdout="{}", stderr=""),
    )

    assert backup_restore_rehearsal.main() == 0

    shell_script = captured["shell_script"]
    assert "restore_database_created=false" in shell_script
    assert "if [[ \"$restore_database_created\" == true ]]" in shell_script
    assert "bit_xor(hashtextextended(row_to_json(t)::text, 0))" in shell_script
    assert "source_counts\" != \"$restored_counts" in shell_script
    assert "Refusing to replace existing restore database" in shell_script
