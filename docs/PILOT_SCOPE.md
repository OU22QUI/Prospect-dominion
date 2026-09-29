# Pilot scope

## In scope

One customer-controlled deployment, one workspace, up to five named users, about 200 accounts, one governed workflow, one or two data sources, and mandatory operator approval before a future external send.

The vertical slice is: ingest one source, normalize with provenance, deterministic score and explanation, prioritise, recommend an action, request approval, send through one provider, ingest provider outcome, and record an audit event.

## Implemented pilot path

The versioned `/v1` API uses a Postgres repository when `PD_STORE_BACKEND=postgres`. It supports first-owner bootstrap, password-based server-issued signed sessions, tenant-scoped owner/operator/viewer roles, CSV signal import with provenance and idempotency, validated deterministic ICP rules, score explanations and priority queue, approval requests/decisions, suppression checks, Resend send reservations, signed Resend webhook processing, outcomes, and append-only audit records. It does not trust the legacy shared API key or client-supplied role headers.

The operator app at `/app` is an API-connected pilot console: a signed-in operator can import CSV signals, set rules, score accounts, inspect provenance, request/decide approval, send an approved action, and inspect outcomes/audit history. It does not use browser storage as the source of truth. Session storage holds only the bearer session token for the active browser tab.

## Remaining validation before customer data

The local isolated-data backup/restore rehearsal passed on 2026-09-29; this does not replace a rehearsal in the customer-specific deployment. Before customer-data use, the deployment still requires a live Compose/Postgres run, real HTTPS/domain configuration, tested Resend credentials/webhook registration, independent security review, a customer-environment backup/restore rehearsal, and controlled internal dogfood. The legacy unversioned API remains demo compatibility code and is not the pilot API.

## Explicitly out of scope

Full OSINT, crawl pipelines, graph routing, vector RAG, LLM routing, autonomous sending, Postal warm-up infrastructure, LiveKit, n8n as a critical path, multi-tenant self-serve SaaS, white-labeling, and fabricated performance claims.
