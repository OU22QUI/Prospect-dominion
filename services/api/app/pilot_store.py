"""Tenant-scoped Postgres repository for the commercial-pilot API.

This intentionally uses explicit SQL so tenant filters and state transitions are
visible in review. It is not used by the public demo or legacy endpoints.
"""

from __future__ import annotations

import json
import os
from hashlib import sha256
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


class PilotStore:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("PG_DSN")
        if not self.dsn:
            raise RuntimeError("PG_DSN is required for the Postgres pilot store")

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Cursor[dict[str, Any]]]:
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                yield cursor
            connection.commit()

    @staticmethod
    def _json(value: dict[str, Any] | None = None) -> str:
        return json.dumps(value or {}, default=lambda item: item.isoformat() if isinstance(item, datetime) else str(item))

    def bootstrap(self, *, tenant_slug: str, tenant_name: str, email: str, display_name: str, password_hash: str) -> dict[str, str]:
        with self.transaction() as cursor:
            cursor.execute("INSERT INTO bootstrap_guard (id) VALUES (true) ON CONFLICT DO NOTHING RETURNING id")
            if cursor.fetchone() is None:
                raise ValueError("bootstrap is already complete")
            cursor.execute(
                "INSERT INTO tenants (slug, display_name) VALUES (%s, %s) RETURNING id",
                (tenant_slug, tenant_name),
            )
            tenant_id = str(cursor.fetchone()["id"])
            cursor.execute("UPDATE bootstrap_guard SET tenant_id = %s WHERE id = true", (tenant_id,))
            cursor.execute(
                "INSERT INTO users (email, display_name, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (email.lower(), display_name, password_hash),
            )
            user_id = str(cursor.fetchone()["id"])
            cursor.execute("SELECT id FROM roles WHERE name = 'owner'")
            role_id = cursor.fetchone()["id"]
            cursor.execute(
                "INSERT INTO workspace_memberships (tenant_id, user_id, role_id) VALUES (%s, %s, %s)",
                (tenant_id, user_id, role_id),
            )
            self._audit(cursor, tenant_id, user_id, "auth.bootstrap", "tenant", tenant_id, {"email": email.lower()})
            return {"tenant_id": tenant_id, "user_id": user_id, "role": "owner"}

    def bootstrap_tenant_id(self) -> str | None:
        with self.transaction() as cursor:
            cursor.execute("SELECT tenant_id FROM bootstrap_guard WHERE id = true")
            record = cursor.fetchone()
            return str(record["tenant_id"]) if record and record["tenant_id"] else None

    def authenticate(self, email: str) -> dict[str, Any] | None:
        with self.transaction() as cursor:
            cursor.execute(
                """
                SELECT u.id AS user_id, u.password_hash, u.is_active, m.tenant_id, r.name AS role
                FROM users u
                JOIN workspace_memberships m ON m.user_id = u.id AND m.deleted_at IS NULL
                JOIN roles r ON r.id = m.role_id
                WHERE u.email = %s AND u.deleted_at IS NULL
                """,
                (email.lower(),),
            )
            return cursor.fetchone()

    def create_user(self, tenant_id: str, actor_id: str, email: str, display_name: str, password_hash: str, role: str) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute("SELECT id FROM roles WHERE name = %s", (role,))
            role_record = cursor.fetchone()
            if role_record is None:
                raise ValueError("unsupported role")
            cursor.execute(
                "INSERT INTO users (email, display_name, password_hash) VALUES (%s, %s, %s) RETURNING id, email, display_name",
                (email.lower(), display_name, password_hash),
            )
            user = cursor.fetchone()
            cursor.execute("INSERT INTO workspace_memberships (tenant_id, user_id, role_id) VALUES (%s, %s, %s)", (tenant_id, user["id"], role_record["id"]))
            self._audit(cursor, tenant_id, actor_id, "user.created", "user", str(user["id"]), {"role": role, "email": user["email"]})
            return {**user, "role": role}

    def list_users(self, tenant_id: str) -> list[dict[str, Any]]:
        with self.transaction() as cursor:
            cursor.execute(
                """SELECT u.id, u.email, u.display_name, u.is_active, r.name AS role, m.created_at
                   FROM users u JOIN workspace_memberships m ON m.user_id = u.id JOIN roles r ON r.id = m.role_id
                   WHERE m.tenant_id = %s AND m.deleted_at IS NULL AND u.deleted_at IS NULL ORDER BY m.created_at""",
                (tenant_id,),
            )
            return list(cursor.fetchall())

    def set_user_role(self, tenant_id: str, actor_id: str, user_id: str, role: str) -> dict[str, Any] | None:
        with self.transaction() as cursor:
            cursor.execute(
                """UPDATE workspace_memberships m SET role_id = r.id
                   FROM roles r WHERE m.tenant_id = %s AND m.user_id = %s AND r.name = %s AND m.deleted_at IS NULL
                   RETURNING m.user_id""",
                (tenant_id, user_id, role),
            )
            updated = cursor.fetchone()
            if updated:
                self._audit(cursor, tenant_id, actor_id, "user.role_changed", "user", user_id, {"role": role})
                return {"user_id": str(updated["user_id"]), "role": role}
            return None

    def principal(self, user_id: str, tenant_id: str) -> dict[str, Any] | None:
        with self.transaction() as cursor:
            cursor.execute(
                """
                SELECT u.id AS user_id, u.email, u.display_name, r.name AS role, m.tenant_id
                FROM users u
                JOIN workspace_memberships m ON m.user_id = u.id AND m.deleted_at IS NULL
                JOIN roles r ON r.id = m.role_id
                WHERE u.id = %s AND m.tenant_id = %s AND u.is_active AND u.deleted_at IS NULL
                """,
                (user_id, tenant_id),
            )
            return cursor.fetchone()

    def _audit(self, cursor: psycopg.Cursor[Any], tenant_id: str, actor_id: str | None, event_type: str, entity_type: str, entity_id: str, details: dict[str, Any]) -> None:
        cursor.execute(
            """INSERT INTO audit_events (tenant_id, actor_user_id, event_type, entity_type, entity_id, details)
               VALUES (%s, %s, %s, %s, %s, %s::jsonb)""",
            (tenant_id, actor_id, event_type, entity_type, entity_id, self._json(details)),
        )

    def _feedback(self, cursor: psycopg.Cursor[Any], tenant_id: str, thread_id: str, feedback_type: str, *, approval_id: str | None = None, send_attempt_id: str | None = None, details: dict[str, Any] | None = None) -> None:
        cursor.execute("SELECT account_id FROM threads WHERE tenant_id = %s AND thread_id = %s", (tenant_id, thread_id))
        thread = cursor.fetchone()
        cursor.execute(
            """INSERT INTO action_feedback (tenant_id, approval_id, send_attempt_id, thread_id, account_id, feedback_type, details)
               VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)""",
            (tenant_id, approval_id, send_attempt_id, thread_id, thread["account_id"] if thread else None, feedback_type, self._json(details)),
        )

    def audit(self, tenant_id: str, actor_id: str | None, event_type: str, entity_type: str, entity_id: str, details: dict[str, Any]) -> None:
        with self.transaction() as cursor:
            self._audit(cursor, tenant_id, actor_id, event_type, entity_type, entity_id, details)

    def list_records(self, table: str, tenant_id: str, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        allowed = {"accounts", "people", "threads", "events", "outcomes", "approvals", "audit_events", "source_connections", "ingest_failures", "action_feedback"}
        if table not in allowed:
            raise ValueError("unsupported table")
        with self.transaction() as cursor:
            deleted = " AND deleted_at IS NULL" if table not in {"events", "outcomes", "approvals", "audit_events", "ingest_failures", "action_feedback"} else ""
            cursor.execute(f"SELECT count(*) AS count FROM {table} WHERE tenant_id = %s{deleted}", (tenant_id,))
            total = int(cursor.fetchone()["count"])
            if table in {"events", "outcomes", "audit_events", "action_feedback"}:
                order = "occurred_at DESC"
            elif table == "approvals":
                order = "requested_at DESC"
            else:
                order = "created_at DESC"
            cursor.execute(f"SELECT * FROM {table} WHERE tenant_id = %s{deleted} ORDER BY {order} LIMIT %s OFFSET %s", (tenant_id, limit, offset))
            return list(cursor.fetchall()), total

    def create_account(self, tenant_id: str, actor_id: str, record: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO accounts (tenant_id, id, domain, legal_name, display_name, industry, icp_score, enrichment)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                   RETURNING *""",
                (tenant_id, record["id"], record["domain"], record.get("legal_name"), record.get("display_name"), record.get("industry"), record.get("icp_score"), self._json(record.get("enrichment"))),
            )
            created = cursor.fetchone()
            self._audit(cursor, tenant_id, actor_id, "account.created", "account", record["id"], {"domain": record["domain"]})
            return created

    def create_person(self, tenant_id: str, actor_id: str, record: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO people (tenant_id, id, account_id, full_name, email, title, seniority, role_function, linkedin_url, psychographics)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb) RETURNING *""",
                (tenant_id, record["id"], record.get("account_id"), record.get("full_name"), record.get("email"), record.get("title"), record.get("seniority"), record.get("role_function"), record.get("linkedin_url"), self._json(record.get("psychographics"))),
            )
            created = cursor.fetchone()
            self._audit(cursor, tenant_id, actor_id, "person.created", "person", record["id"], {})
            return created

    def create_thread(self, tenant_id: str, actor_id: str, record: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO threads (tenant_id, thread_id, person_id, account_id, campaign_id, opp_stage, consent_basis, next_action_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
                (tenant_id, record["thread_id"], record["person_id"], record.get("account_id"), record.get("campaign_id"), record.get("opp_stage", "new"), record.get("consent_basis", "none"), record.get("next_action_at")),
            )
            created = cursor.fetchone()
            self._audit(cursor, tenant_id, actor_id, "thread.created", "thread", record["thread_id"], {})
            return created

    def get_settings(self, tenant_id: str) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute("SELECT icp_rules, approval_policy FROM workspace_settings WHERE tenant_id = %s", (tenant_id,))
            result = cursor.fetchone()
            return result or {"icp_rules": {"version": 1, "base_score": 0, "rules": []}, "approval_policy": {"require_approval": True}}

    def save_rules(self, tenant_id: str, actor_id: str, rules: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO workspace_settings (tenant_id, icp_rules, updated_by)
                   VALUES (%s, %s::jsonb, %s)
                   ON CONFLICT (tenant_id) DO UPDATE SET icp_rules = EXCLUDED.icp_rules, updated_by = EXCLUDED.updated_by, updated_at = now()
                   RETURNING icp_rules""",
                (tenant_id, self._json(rules), actor_id),
            )
            result = cursor.fetchone()
            self._audit(cursor, tenant_id, actor_id, "settings.icp_rules_updated", "workspace", tenant_id, {})
            return result

    def events_for_account(self, tenant_id: str, account_id: str) -> list[dict[str, Any]]:
        with self.transaction() as cursor:
            cursor.execute(
                """SELECT e.* FROM events e JOIN threads t ON t.tenant_id = e.tenant_id AND t.thread_id = e.thread_id
                   WHERE e.tenant_id = %s AND t.account_id = %s ORDER BY e.occurred_at DESC""",
                (tenant_id, account_id),
            )
            return list(cursor.fetchall())

    def save_score(self, tenant_id: str, actor_id: str, account_id: str, result: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO account_scores (tenant_id, account_id, score, explanation)
                   VALUES (%s, %s, %s, %s::jsonb)
                   ON CONFLICT (tenant_id, account_id) DO UPDATE SET score = EXCLUDED.score, explanation = EXCLUDED.explanation, computed_at = now()
                   RETURNING *""",
                (tenant_id, account_id, result["score"], self._json(result["explanation"])),
            )
            saved = cursor.fetchone()
            cursor.execute("UPDATE recommended_actions SET status = 'superseded' WHERE tenant_id = %s AND account_id = %s AND status = 'active'", (tenant_id, account_id))
            cursor.execute(
                """INSERT INTO recommended_actions (tenant_id, account_id, action_type, confidence, rationale)
                   VALUES (%s, %s, %s, %s, %s::jsonb) RETURNING *""",
                (tenant_id, account_id, result["action_type"], result["confidence"], self._json(result["explanation"])),
            )
            action = cursor.fetchone()
            self._audit(cursor, tenant_id, actor_id, "score.computed", "account", account_id, {"score": result["score"], "action_id": str(action["id"])})
            return {"score": saved, "action": action}

    def priority_queue(self, tenant_id: str, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        with self.transaction() as cursor:
            cursor.execute("SELECT count(*) AS count FROM account_scores WHERE tenant_id = %s", (tenant_id,))
            total = int(cursor.fetchone()["count"])
            cursor.execute(
                """SELECT a.*, s.score, s.explanation, s.computed_at, r.id AS action_id, r.action_type, r.confidence, r.rationale
                   FROM account_scores s JOIN accounts a ON a.tenant_id = s.tenant_id AND a.id = s.account_id
                   LEFT JOIN LATERAL (SELECT * FROM recommended_actions r WHERE r.tenant_id = s.tenant_id AND r.account_id = s.account_id AND r.status = 'active' ORDER BY r.created_at DESC LIMIT 1) r ON true
                   WHERE s.tenant_id = %s AND a.deleted_at IS NULL ORDER BY s.score DESC, s.computed_at DESC LIMIT %s OFFSET %s""",
                (tenant_id, limit, offset),
            )
            return list(cursor.fetchall()), total

    def request_approval(self, tenant_id: str, actor_id: str, record: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO approvals (tenant_id, thread_id, requested_by, action_type, action_payload, idempotency_key, expires_at)
                   VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s) RETURNING *""",
                (tenant_id, record["thread_id"], actor_id, record["action_type"], self._json(record.get("action_payload")), record["idempotency_key"], record.get("expires_at")),
            )
            approval = cursor.fetchone()
            self._audit(cursor, tenant_id, actor_id, "approval.requested", "approval", str(approval["id"]), {"thread_id": record["thread_id"]})
            return approval

    def decide_approval(self, tenant_id: str, actor_id: str, approval_id: str, status: str, reason: str | None) -> dict[str, Any] | None:
        with self.transaction() as cursor:
            cursor.execute(
                """UPDATE approvals SET status = %s, decided_by = %s, decision_reason = %s, decided_at = now()
                   WHERE id = %s AND tenant_id = %s AND status = 'pending' AND (expires_at IS NULL OR expires_at > now()) RETURNING *""",
                (status, actor_id, reason, approval_id, tenant_id),
            )
            approval = cursor.fetchone()
            if approval:
                self._audit(cursor, tenant_id, actor_id, f"approval.{status}", "approval", approval_id, {"reason": reason})
                self._feedback(cursor, tenant_id, approval["thread_id"], status, approval_id=approval_id, details={"reason": reason})
            return approval

    def import_csv_signals(self, tenant_id: str, actor_id: str, source_name: str, rows: list[dict[str, Any]], cursor_value: str) -> dict[str, int | str]:
        """Normalize a checked CSV in one transaction; replays create no duplicate events."""
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO source_connections (tenant_id, source_type, display_name, status)
                   VALUES (%s, 'csv', %s, 'active')
                   ON CONFLICT (tenant_id, display_name) DO UPDATE SET status = 'active', updated_at = now()
                   RETURNING id""",
                (tenant_id, source_name),
            )
            source_id = str(cursor.fetchone()["id"])
            cursor.execute("UPDATE ingest_failures SET resolved_at = now() WHERE tenant_id = %s AND source_connection_id = %s AND idempotency_key = %s AND resolved_at IS NULL", (tenant_id, source_id, cursor_value))
            created = 0
            deduplicated = 0
            for row in rows:
                # Domain is the connector's canonical account key, so a replay
                # or a later row cannot point a person at a conflicting account.
                account_id = row["domain"].lower()
                person_id = row.get("person_id") or row["email"].lower()
                thread_id = row.get("thread_id") or f"csv:{row['external_id']}"
                cursor.execute(
                    """INSERT INTO accounts (tenant_id, id, domain, display_name)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (tenant_id, domain) DO UPDATE SET display_name = COALESCE(EXCLUDED.display_name, accounts.display_name), updated_at = now()""",
                    (tenant_id, account_id, row["domain"].lower(), row.get("company") or row["domain"]),
                )
                cursor.execute(
                    """INSERT INTO people (tenant_id, id, account_id, full_name, email)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (tenant_id, id) DO UPDATE SET full_name = EXCLUDED.full_name, email = EXCLUDED.email, updated_at = now()""",
                    (tenant_id, person_id, account_id, row["full_name"], row["email"].lower()),
                )
                cursor.execute(
                    """INSERT INTO threads (tenant_id, thread_id, person_id, account_id, opp_stage, consent_basis)
                       VALUES (%s, %s, %s, %s, 'new', %s)
                       ON CONFLICT (tenant_id, thread_id) DO UPDATE SET consent_basis = EXCLUDED.consent_basis, updated_at = now()""",
                    (tenant_id, thread_id, person_id, account_id, row["consent_basis"]),
                )
                event_id = f"csv:{sha256(row['idempotency_key'].encode()).hexdigest()[:24]}"
                cursor.execute(
                    """INSERT INTO events (tenant_id, event_id, thread_id, event_type, source, source_connection_id, external_id, raw_ref, payload, occurred_at, idempotency_key)
                       VALUES (%s, %s, %s, %s, 'csv', %s, %s, %s, %s::jsonb, %s, %s)
                       ON CONFLICT (tenant_id, idempotency_key) DO NOTHING RETURNING event_id""",
                    (tenant_id, event_id, thread_id, row["signal_type"], source_id, row["external_id"], f"csv:{cursor_value}:line:{row['line_number']}", self._json({"source_trust": row.get("source_trust") or "1", "line_number": row["line_number"]}), row["observed_at"], row["idempotency_key"]),
                )
                if cursor.fetchone():
                    created += 1
                else:
                    deduplicated += 1
            cursor.execute(
                """INSERT INTO sync_cursors (source_connection_id, cursor_value, last_success_at)
                   VALUES (%s, %s, now()) ON CONFLICT (source_connection_id)
                   DO UPDATE SET cursor_value = EXCLUDED.cursor_value, last_success_at = EXCLUDED.last_success_at, updated_at = now()""",
                (source_id, cursor_value),
            )
            self._audit(cursor, tenant_id, actor_id, "source.csv_imported", "source_connection", source_id, {"rows": len(rows), "created": created, "deduplicated": deduplicated})
            return {"source_connection_id": source_id, "received": len(rows), "created": created, "deduplicated": deduplicated}

    def record_csv_failure(self, tenant_id: str, actor_id: str, source_name: str, import_key: str, error: str) -> None:
        """Persist a failed upload so an operator can retry the same source safely."""
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO source_connections (tenant_id, source_type, display_name, status, last_error)
                   VALUES (%s, 'csv', %s, 'error', %s)
                   ON CONFLICT (tenant_id, display_name) DO UPDATE SET status = 'error', last_error = EXCLUDED.last_error, updated_at = now()
                   RETURNING id""",
                (tenant_id, source_name, error[:1000]),
            )
            source_id = cursor.fetchone()["id"]
            cursor.execute(
                """INSERT INTO ingest_failures (tenant_id, source_connection_id, idempotency_key, error_detail, next_retry_at)
                   VALUES (%s, %s, %s, %s, now() + interval '30 seconds')
                   ON CONFLICT (tenant_id, source_connection_id, idempotency_key)
                   DO UPDATE SET attempts = ingest_failures.attempts + 1, error_detail = EXCLUDED.error_detail,
                                 next_retry_at = now() + make_interval(secs => LEAST(3600, 30 * power(2, ingest_failures.attempts)::int))
                   RETURNING id, attempts""",
                (tenant_id, source_id, import_key, error[:4000]),
            )
            failure = cursor.fetchone()
            self._audit(cursor, tenant_id, actor_id, "source.csv_failed", "ingest_failure", str(failure["id"]), {"attempts": failure["attempts"], "error": error[:250]})

    def claim_approved_send(self, tenant_id: str, actor_id: str, approval_id: str, idempotency_key: str) -> dict[str, Any]:
        """Atomically check approval/suppression and reserve exactly one send attempt."""
        with self.transaction() as cursor:
            cursor.execute(
                """SELECT a.*, t.account_id, t.consent_basis FROM approvals a JOIN threads t ON t.tenant_id = a.tenant_id AND t.thread_id = a.thread_id
                   WHERE a.id = %s AND a.tenant_id = %s FOR UPDATE""",
                (approval_id, tenant_id),
            )
            approval = cursor.fetchone()
            if not approval or approval["status"] != "approved":
                raise ValueError("an approved approval is required before sending")
            if approval["consent_basis"] not in {"consent", "legitimate_interest"}:
                self._audit(cursor, tenant_id, actor_id, "send.blocked_no_legal_basis", "approval", approval_id, {"consent_basis": approval.get("consent_basis")})
                raise ValueError("a permitted consent/legal basis is required before sending")
            payload = approval["action_payload"]
            email = str(payload.get("to", "")).lower()
            if not email or "@" not in email:
                raise ValueError("approved action does not contain a valid recipient")
            cursor.execute("SELECT id FROM suppression_entries WHERE tenant_id = %s AND email = %s AND removed_at IS NULL", (tenant_id, email))
            if cursor.fetchone():
                cursor.execute(
                    """INSERT INTO send_attempts (tenant_id, approval_id, thread_id, recipient_email, provider, idempotency_key, status)
                       VALUES (%s, %s, %s, %s, 'resend', %s, 'suppressed') ON CONFLICT (tenant_id, idempotency_key) DO NOTHING RETURNING *""",
                    (tenant_id, approval_id, approval["thread_id"], email, idempotency_key),
                )
                attempt = cursor.fetchone()
                self._audit(cursor, tenant_id, actor_id, "send.suppressed", "approval", approval_id, {"email": email})
                if attempt:
                    self._feedback(cursor, tenant_id, approval["thread_id"], "suppressed", approval_id=approval_id, send_attempt_id=str(attempt["id"]), details={"email": email})
                return {"attempt": attempt, "payload": payload, "should_send": False}
            cursor.execute(
                """INSERT INTO send_attempts (tenant_id, approval_id, thread_id, recipient_email, provider, idempotency_key, status)
                   VALUES (%s, %s, %s, %s, 'resend', %s, 'queued') ON CONFLICT (tenant_id, idempotency_key) DO NOTHING RETURNING *""",
                (tenant_id, approval_id, approval["thread_id"], email, idempotency_key),
            )
            attempt = cursor.fetchone()
            if attempt is None:
                cursor.execute("SELECT * FROM send_attempts WHERE tenant_id = %s AND idempotency_key = %s", (tenant_id, idempotency_key))
                attempt = cursor.fetchone()
                return {"attempt": attempt, "payload": payload, "should_send": False}
            self._audit(cursor, tenant_id, actor_id, "send.queued", "send_attempt", str(attempt["id"]), {"approval_id": approval_id})
            return {"attempt": attempt, "payload": payload, "should_send": True}

    def record_send_result(self, tenant_id: str, actor_id: str, attempt_id: str, *, message_id: str | None = None, error: str | None = None) -> dict[str, Any]:
        with self.transaction() as cursor:
            if message_id:
                cursor.execute("UPDATE send_attempts SET status = 'sent', provider_message_id = %s, sent_at = now(), updated_at = now() WHERE id = %s AND tenant_id = %s RETURNING *", (message_id, attempt_id, tenant_id))
                event_type = "send.sent"
            else:
                cursor.execute("UPDATE send_attempts SET status = 'failed', error_detail = %s, updated_at = now() WHERE id = %s AND tenant_id = %s RETURNING *", (error, attempt_id, tenant_id))
                event_type = "send.failed"
            attempt = cursor.fetchone()
            if attempt:
                self._audit(cursor, tenant_id, actor_id, event_type, "send_attempt", attempt_id, {"provider_message_id": message_id, "error": error})
                self._feedback(cursor, tenant_id, attempt["thread_id"], "sent" if message_id else "failed", approval_id=str(attempt["approval_id"]), send_attempt_id=attempt_id, details={"provider_message_id": message_id, "error": error})
            return attempt

    def receive_resend_webhook(self, tenant_id: str, event: dict[str, Any]) -> bool:
        event_id = str(event.get("id") or event.get("data", {}).get("email_id") or "")
        event_type = str(event.get("type") or "")
        message_id = str(event.get("data", {}).get("email_id") or "")
        if not event_id or not event_type:
            raise ValueError("webhook lacks id or type")
        if event_type in {"contact.unsubscribed", "email.unsubscribed"}:
            email = str(event.get("data", {}).get("email") or event.get("data", {}).get("contact", {}).get("email") or "").lower()
            if "@" not in email:
                raise ValueError("unsubscribe webhook lacks an email address")
            with self.transaction() as cursor:
                cursor.execute("INSERT INTO webhook_receipts (tenant_id, provider, event_id, payload) VALUES (%s, 'resend', %s, %s::jsonb) ON CONFLICT DO NOTHING RETURNING event_id", (tenant_id, event_id, self._json(event)))
                if cursor.fetchone() is None:
                    return False
                cursor.execute("INSERT INTO suppression_entries (tenant_id, email, reason, source) VALUES (%s, %s, 'unsubscribe', 'resend_webhook') ON CONFLICT (tenant_id, email) DO NOTHING", (tenant_id, email))
                self._audit(cursor, tenant_id, None, "webhook.unsubscribe", "suppression", email, {"event_id": event_id})
                return True
        if not message_id:
            raise ValueError("webhook lacks email id")
        status_map = {"email.delivered": "delivered", "email.bounced": "bounced", "email.complained": "complained", "email.received": "replied"}
        if event_type not in status_map:
            return False
        with self.transaction() as cursor:
            cursor.execute(
                """INSERT INTO webhook_receipts (tenant_id, provider, event_id, payload) VALUES (%s, 'resend', %s, %s::jsonb)
                   ON CONFLICT DO NOTHING RETURNING event_id""",
                (tenant_id, event_id, self._json(event)),
            )
            if cursor.fetchone() is None:
                return False
            cursor.execute("SELECT * FROM send_attempts WHERE tenant_id = %s AND provider = 'resend' AND provider_message_id = %s FOR UPDATE", (tenant_id, message_id))
            attempt = cursor.fetchone()
            if attempt is None:
                return True
            status = status_map[event_type]
            cursor.execute("UPDATE send_attempts SET status = %s, updated_at = now() WHERE id = %s", (status, attempt["id"]))
            if status in {"bounced", "complained"}:
                cursor.execute(
                    """INSERT INTO suppression_entries (tenant_id, email, reason, source)
                       VALUES (%s, %s, %s, 'resend_webhook') ON CONFLICT (tenant_id, email) DO NOTHING""",
                    (tenant_id, attempt["recipient_email"], status),
                )
            cursor.execute("SELECT account_id FROM threads WHERE tenant_id = %s AND thread_id = %s", (tenant_id, attempt["thread_id"]))
            account = cursor.fetchone()
            outcome_id = f"resend:{event_id}"
            cursor.execute(
                """INSERT INTO outcomes (tenant_id, outcome_id, thread_id, account_id, stage_to, reason, attributed_signal)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (tenant_id, outcome_id, attempt["thread_id"], account["account_id"] if account else None, status, f"Resend {event_type}", event_type),
            )
            self._audit(cursor, tenant_id, None, f"webhook.{event_type}", "send_attempt", str(attempt["id"]), {"event_id": event_id})
            self._feedback(cursor, tenant_id, attempt["thread_id"], status, approval_id=str(attempt["approval_id"]), send_attempt_id=str(attempt["id"]), details={"event_id": event_id})
            return True
