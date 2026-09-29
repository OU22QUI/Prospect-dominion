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


def main() -> int:
    restore_database = os.getenv("PD_RESTORE_TEST_DB", f"pd_restore_{uuid.uuid4().hex[:12]}")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", restore_database):
        print("PD_RESTORE_TEST_DB must be a valid unquoted PostgreSQL identifier", file=sys.stderr)
        return 2

    shell_script = f"""
set -euo pipefail
restore_database='{restore_database}'
backup_file="/tmp/${{restore_database}}.dump"
cleanup() {{
    dropdb -U aethonex --if-exists "$restore_database" >/dev/null 2>&1 || true
    rm -f "$backup_file"
}}
trap cleanup EXIT

count_rows() {{
    local database="$1"
    local total=0
    while IFS= read -r table; do
        [[ -n "$table" ]] || continue
        count="$(psql -v ON_ERROR_STOP=1 -U aethonex -d "$database" -Atc "SELECT count(*) FROM $table")"
        total=$((total + count))
    done < <(psql -v ON_ERROR_STOP=1 -U aethonex -d "$database" -Atc "SELECT quote_ident(schemaname) || '.' || quote_ident(tablename) FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
    printf '%s' "$total"
}}

source_tables="$(psql -v ON_ERROR_STOP=1 -U aethonex -d prospect_dominion -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")"
source_rows="$(count_rows prospect_dominion)"
pg_dump -U aethonex -d prospect_dominion -Fc > "$backup_file"
createdb -U aethonex "$restore_database"
pg_restore --exit-on-error -U aethonex -d "$restore_database" "$backup_file"
restored_tables="$(psql -v ON_ERROR_STOP=1 -U aethonex -d "$restore_database" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")"
restored_rows="$(count_rows "$restore_database")"
if [[ "$source_tables" -eq 0 || "$source_tables" -ne "$restored_tables" || "$source_rows" -ne "$restored_rows" ]]; then
    printf 'Restore mismatch: source tables=%s rows=%s; restored tables=%s rows=%s\\n' "$source_tables" "$source_rows" "$restored_tables" "$restored_rows" >&2
    exit 1
fi
printf '{{"status":"passed","source_tables":%s,"restored_tables":%s,"source_rows":%s,"restored_rows":%s}}\\n' "$source_tables" "$restored_tables" "$source_rows" "$restored_rows"
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
