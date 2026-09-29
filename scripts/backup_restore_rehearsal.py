#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PG_CONTAINER = "prospect-dominion-postgres-1"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(REPO_ROOT), text=True, capture_output=True, check=check)


def main() -> int:
    shell_script = """
set -e
pg_dump -U aethonex -d prospect_dominion -Fc > /tmp/prospect-dominion-backup.dump
if ! psql -U aethonex -d postgres -tAc \"SELECT 1 FROM pg_database WHERE datname = 'prospect_dominion_restore_test'\" | grep -q 1; then
  createdb -U aethonex prospect_dominion_restore_test
fi
pg_restore -U aethonex -d prospect_dominion_restore_test --clean --if-exists /tmp/prospect-dominion-backup.dump
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
        "core",
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

    payload = subprocess.run(
        [
            "python",
            "-c",
            "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8010/ready', timeout=10).read().decode()); print(json.dumps(data, indent=2))",
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
