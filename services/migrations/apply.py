"""Apply ordered, idempotent Postgres migrations for the pilot profile."""

from __future__ import annotations

import os
import time
from pathlib import Path

import psycopg


MIGRATIONS_DIR = Path(os.getenv("MIGRATIONS_DIR", "/migrations/postgres"))
if not MIGRATIONS_DIR.exists():  # Supports CI/local migration invocation.
    MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "postgres"


def connect(dsn: str) -> psycopg.Connection:
    for attempt in range(1, 31):
        try:
            return psycopg.connect(dsn)
        except psycopg.OperationalError:
            if attempt == 30:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")  # pragma: no cover


def main() -> None:
    with connect(os.environ["PG_DSN"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cursor.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if migration.name in applied:
                    continue
                cursor.execute(migration.read_text(encoding="utf-8"))
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (migration.name,))
                connection.commit()
                print(f"applied {migration.name}")


if __name__ == "__main__":
    main()
