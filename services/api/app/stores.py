from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def resolve_project_root() -> Path:
    file_path = Path(__file__).resolve()
    search_roots = [file_path, *file_path.parents, Path.cwd(), *Path.cwd().parents]
    seen: set[Path] = set()

    for candidate in search_roots:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.exists():
            continue
        if any((resolved / marker).exists() for marker in ("docker-compose.yml", "README.md", ".git")):
            return resolved

    for candidate in file_path.parents:
        if candidate.name == "services":
            return candidate.parent
    return file_path.parent.parent if len(file_path.parents) >= 2 else file_path.parent


class SQLiteStore:
    def __init__(self, db_path: str | None = None) -> None:
        configured_path = db_path or os.getenv("PD_DB_PATH")
        if configured_path:
            self.db_path = Path(configured_path).expanduser().resolve()
        else:
            project_root = resolve_project_root()
            self.db_path = project_root / "data" / "prospect_dominion.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _serialize(payload: dict[str, Any]) -> str:
        return json.dumps(payload, default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value))

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS people (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    thread_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @property
    def accounts(self) -> dict[str, dict[str, Any]]:
        return {row["id"]: row for row in self._read_payloads("accounts")}

    @property
    def people(self) -> dict[str, dict[str, Any]]:
        return {row["id"]: row for row in self._read_payloads("people")}

    @property
    def threads(self) -> dict[str, dict[str, Any]]:
        return {row["thread_id"]: row for row in self._read_payloads("threads")}

    @property
    def events(self) -> dict[str, dict[str, Any]]:
        return {row["event_id"]: row for row in self._read_payloads("events")}

    @property
    def outcomes(self) -> dict[str, dict[str, Any]]:
        return {row["outcome_id"]: row for row in self._read_payloads("outcomes")}

    def _read_payloads(self, table_name: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT payload FROM {table_name}").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def _write_record(self, table_name: str, key_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} ({key_name}, payload) VALUES (?, ?)",
                (payload[key_name], self._serialize(payload)),
            )
            conn.commit()
        return payload

    def upsert_account(self, account: dict[str, Any]) -> dict[str, Any]:
        return self._write_record("accounts", "id", account)

    def upsert_person(self, person: dict[str, Any]) -> dict[str, Any]:
        return self._write_record("people", "id", person)

    def add_thread(self, thread: dict[str, Any]) -> dict[str, Any]:
        return self._write_record("threads", "thread_id", thread)

    def add_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return self._write_record("events", "event_id", event)

    def add_outcome(self, outcome: dict[str, Any]) -> dict[str, Any]:
        return self._write_record("outcomes", "outcome_id", outcome)

    def list_events(self) -> list[dict[str, Any]]:
        return self._read_payloads("events")

    def list_outcomes(self) -> list[dict[str, Any]]:
        return self._read_payloads("outcomes")

    def list_threads(self) -> list[dict[str, Any]]:
        return self._read_payloads("threads")


store = SQLiteStore()
