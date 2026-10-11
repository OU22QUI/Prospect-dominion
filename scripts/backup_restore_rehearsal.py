#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_PORT = os.getenv("API_PORT", "8010")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(REPO_ROOT), text=True, capture_output=True, check=check)


def validate_restore_database(database: str) -> None:
    if not re.fullmatch(r"pd_restore_[a-zA-Z0-9_]{1,50}", database):
        raise ValueError("restore database name must use the pd_restore_ prefix and contain only letters, digits, or underscores")


def main() -> int:
    restore_database = os.getenv("PD_RESTORE_TEST_DB", f"pd_restore_{uuid.uuid4().hex[:12]}")
    try:
        validate_restore_database(restore_database)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    shell_script = f"""
set -euo pipefail
restore_database='{restore_database}'
backup_file="/tmp/${{restore_database}}.dump"
restore_database_created=false
cleanup() {{
    if [[ "$restore_database_created" == true ]]; then
        dropdb -U aethonex "$restore_database" >/dev/null
    fi
    rm -f "$backup_file"
}}
trap cleanup EXIT

count_table_rows() {{
    local database="$1"
    local table
    while IFS= read -r table; do
        [[ -n "$table" ]] || continue
        fingerprint="$(psql -v ON_ERROR_STOP=1 -U aethonex -d "$database" -Atc "SELECT count(*) || E'\\\\t' || COALESCE(bit_xor(hashtextextended(row_to_json(t)::text, 0)), 0) || E'\\\\t' || COALESCE(sum(hashtextextended(row_to_json(t)::text, 1)::numeric), 0) FROM $table AS t")"
        printf '%s\\t%s\\n' "$table" "$fingerprint"
    done < <(psql -v ON_ERROR_STOP=1 -U aethonex -d "$database" -Atc "SELECT quote_ident(schemaname) || '.' || quote_ident(tablename) FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
}}

total_rows() {{
    awk -F '\\t' '{{total += $2}} END {{print total + 0}}' <<< "$1"
}}

source_tables="$(psql -v ON_ERROR_STOP=1 -U aethonex -d prospect_dominion -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")"
source_counts="$(count_table_rows prospect_dominion)"
source_rows="$(total_rows "$source_counts")"
pg_dump -U aethonex -d prospect_dominion -Fc > "$backup_file"
if psql -v ON_ERROR_STOP=1 -U aethonex -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '$restore_database'" | grep -q 1; then
    printf 'Refusing to replace existing restore database: %s\\n' "$restore_database" >&2
    exit 1
fi
createdb -U aethonex "$restore_database"
restore_database_created=true
pg_restore --exit-on-error -U aethonex -d "$restore_database" "$backup_file"
restored_tables="$(psql -v ON_ERROR_STOP=1 -U aethonex -d "$restore_database" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")"
restored_counts="$(count_table_rows "$restore_database")"
restored_rows="$(total_rows "$restored_counts")"
if [[ "$source_tables" -eq 0 || "$source_tables" -ne "$restored_tables" || "$source_counts" != "$restored_counts" ]]; then
    printf 'Restore mismatch: source tables=%s rows=%s; restored tables=%s rows=%s\\n' "$source_tables" "$source_rows" "$restored_tables" "$restored_rows" >&2
    diff <(printf '%s\\n' "$source_counts") <(printf '%s\\n' "$restored_counts") >&2 || true
    exit 1
fi
printf '{{"status":"passed","source_tables":%s,"restored_tables":%s,"source_rows":%s,"restored_rows":%s,"per_table_data_fingerprints_verified":true}}\\n' "$source_tables" "$restored_tables" "$source_rows" "$restored_rows"
    """

    result = run(
        "docker",
        "compose",
        "--env-file",
        "deploy/customer.env.example",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.override.yml",
        "--profile",
        "pilot",
        "exec",
        "-T",
        "postgres",
        "bash",
        "-lc",
        shell_script,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return result.returncode

    print(result.stdout.strip())

    payload = subprocess.run(
        [
            "python",
            "-c",
            f"import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:{API_PORT}/ready', timeout=10).read().decode()); print(json.dumps(data, indent=2))",
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    print(payload.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
