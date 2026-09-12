# 🧠 Prospect Dominion — WL1 Outcome Ingest Workflow

> **Doc code:** `FLOW-WL1 v1.0` · **Type:** Executable n8n workflow (importable JSON)
> **Squad:** Learning Crew (L-LEARN) — Harvester
> **Consumes:** outcome events from **every** module — `lead.discovered` · `lead.scored` · `touch.sent` · `reply.classified` · `lead.suppressed` · `meeting.booked` · `meeting.held` · `meeting.no_show` · `lead.dq` · `deal.won` · `deal.lost` · `email.bounced`
> **Emits:** `outcome.logged` (fan-out trigger for WL2 attribution)
> **Companion to:** all `FLOW-*` workflows (this is their shared destination) · L-LEARN §L.3, §L.7, §L.9

---

## §WL1.0 — Why this workflow exists

Every workflow built so far ends with the same phrase: *"…feeds back to Self-Improvement."* **This is that intake.** WL1 is the single, always-on subscriber that turns the system's normal operation into a stream of labeled training data.

Without it, Dominion is a very good machine that stays exactly as good as the day it was built. With it, **the system that closed a deal this week is measurably better at finding the next one.**

WL1 does exactly one thing, and does it with zero loss:

1. **Subscribes** to outcome events from every module.
2. **Normalizes** each into a canonical `outcome_log` record keyed to the shared `thread_id`.
3. **Appends** it immutably (append-only; never updated, never deleted except by consent erasure).
4. **Emits** `outcome.logged` so downstream attribution (WL2) and drift watch (WL6) can react.

> **Prime directive:** every outcome — win, loss, no-show, reply, disqualification, bounce — is a labeled training example. Nothing is wasted. The machine learns from *no* as hard as it learns from *yes*. **Turn this on first and immediately — labels are perishable and cumulative.**

---

## §WL1.1 — Layer stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  INGRESS      bus subscription (wildcard) to all outcome-bearing events │
├──────────────────────────────────────────────────────────────────────┤
│  NORMALIZE    per-source adapter → canonical OutcomeRecord             │
├──────────────────────────────────────────────────────────────────────┤
│  ENRICH-KEY   bind thread_id · cohort tags (ICP seg·persona·source·    │
│               channel·vertical) · consent basis snapshot               │
├──────────────────────────────────────────────────────────────────────┤
│  APPEND       Postgres outcome_log (append-only, immutable)            │
├──────────────────────────────────────────────────────────────────────┤
│  EVIDENCE     Garage pointer to raw artifact (transcript/recording/raw)│
├──────────────────────────────────────────────────────────────────────┤
│  EMIT         outcome.logged → WL2 attribution · WL6 drift watch       │
├──────────────────────────────────────────────────────────────────────┤
│  RESILIENCE   idempotency · DLQ · at-least-once → exactly-once append   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## §WL1.2 — Squad & tool bindings

| Role | Agent / Node | Tools |
|---|---|---|
| **Harvester** | Learning Crew | event bus (wildcard sub), Postgres `outcome_log` |
| **Normalizer** | per-source adapter map | canonical schema validator |
| **Cohort Tagger** | enrichment node | Postgres (lead facts), Neo4j (committee), lookup of ICP seg/persona |
| **Consent Snapshotter** | compliance node | Consent Ledger (basis at time of outcome) |
| **Evidence Linker** | storage node | Garage (S3) object pointers |

---

## §WL1.3 — Outcome sources & the events harvested

| Source module | Outcome events harvested | Why it matters |
|---|---|---|
| **L-GEN** | `lead.discovered` (which source surfaced it; ICP-fit at discovery; triage pass/fail) | Feeds the **Source Genome** — which surfaces yield *payers* |
| **W2 enrichment** | `lead.scored` (enrichment depth, verify tier) | Enrichment ROI |
| **v1.1 [6] scoring** | predicted score vs. actual outcome | **The core training pair** |
| **WO1 dispatch** | `touch.sent` (channel, variant, send time) | Channel/copy attribution inputs |
| **W5 conversation** | `reply.classified`, `objection`, `lead.suppressed` | Reply-rate + objection learning |
| **WV booking** | `meeting.booked`, `meeting.held`, `meeting.no_show`, `lead.dq` | Funnel-floor conversion signal |
| **Human AE / CRM** | `deal.won`, `deal.lost` (deal size, cycle length, loss reason) | The ground-truth label |
| **L-SEND** | `email.bounced`, deliverability outcome | Feeds sending reputation + verify calibration |

> Each record is **immutable, timestamped, and keyed to `thread_id`** — so any outcome can be replayed against the full history that produced it.

---

## §WL1.4 — The canonical OutcomeRecord

```jsonc
{
  "outcome_id": "uuid",              // deterministic from source_event_id (idempotency)
  "thread_id": "uuid",               // the spine — links to full prospect history
  "source_module": "WV | W5 | CRM | ...",
  "event_type": "deal.won | meeting.no_show | reply.classified | ...",
  "occurred_at": "RFC3339",
  "payload": { /* source-specific, schema-validated */ },
  "label": {                          // the supervised signal, where applicable
    "kind": "win | loss | no_show | reply | bounce | dq | fit",
    "value": "…",                     // e.g. deal_size, loss_reason, intent_label
    "polarity": "positive | negative | neutral"
  },
  "cohort": {                         // for sliced learning (§L.4)
    "icp_segment": "…", "persona": "…", "source": "…",
    "channel": "…", "vertical": "…"
  },
  "consent_basis": "…",              // snapshot at time of outcome (compliance)
  "evidence_ref": "garage://…",      // immutable raw artifact pointer
  "predicted": { "score": 0.0, "model_version": "…" }  // for predicted-vs-actual pairs
}
```

> **The `predicted` block is precious.** Capturing the score *and the model version* that produced it, alongside the actual outcome, is what makes the scoring retrainer (WL3/L.5a) possible. Log it at outcome time, not retro-actively.

---

## §WL1.5 — Node graph (importable JSON shape)

```
[Bus Trigger: wildcard outcome.* / deal.* / meeting.* / reply.* / lead.* / email.bounced]
        │
        ▼
[Fn: idempotency guard (outcome_id = hash(source_event_id))] ──dup──▶ [NoOp: ack]
        │
        ▼
[Switch: source_module → per-source Normalizer adapter]
        │
        ▼
[Fn: build canonical OutcomeRecord + schema validate] ──invalid──▶ [DLQ + alert]
        │
        ▼
[Enrich: bind thread_id · cohort tags (Postgres+Neo4j) · consent snapshot]
        │
        ▼
[Link evidence: Garage object pointer]
        │
        ▼
[Postgres: INSERT append-only outcome_log (ON CONFLICT DO NOTHING)]
        │
        ▼
[Emit outcome.logged → WL2 attribution + WL6 drift watch]

  (any node error) ─▶ [DLQ + Langfuse trace + alert]
```

---

## §WL1.6 — Idempotency, ordering & exactly-once append

- **At-least-once in, exactly-once stored.** The bus delivers at-least-once; `outcome_id = hash(source_event_id)` + `INSERT … ON CONFLICT DO NOTHING` guarantees the log never double-counts a redelivered event.
- **Append-only, forever.** No `UPDATE`, no `DELETE` in normal operation. Corrections arrive as *new* records that supersede (event-sourcing style), preserving the full audit trail.
- **Out-of-order tolerant.** Records carry `occurred_at`; attribution (WL2) sorts by it, so late-arriving events (e.g. a `deal.won` weeks after the touch) still credit correctly.
- **The one exception:** **consent erasure** cascades a hard delete/anonymize of a prospect's records *and their training labels* (§WL1.8) — the only writer besides append.

---

## §WL1.7 — Scaling, cost, observability

- **Scaling:** pure ingest — cheap and horizontally scalable off the queue. It is **off the hot path**; it never slows live outreach. Partition `outcome_log` by month for retention/query performance.
- **Cost:** near-zero LLM usage (normalization is deterministic); cost is storage, which is the point — data is the moat.
- **Observability (Langfuse + dashboards):** ingest rate by source, DLQ depth, schema-rejection rate, **label coverage** (what % of touches eventually get a terminal label), and lag between `occurred_at` and log-append.
- **North-star it feeds:** *is win-rate-per-lead trending up cycle over cycle?* — but that's computed downstream; WL1's only KPI is **zero label loss.**

---

## §WL1.8 — Compliance (built in, not bolted on)

- **Consent basis is snapshotted at outcome time** — you can always prove the lawful basis under which a record was created.
- **Right-to-erasure cascades into training data.** When the consent ledger marks a prospect erased, WL1's erasure path purges their `outcome_log` records **and flags their labels for removal from any re-training set.** A forgotten prospect is forgotten by the models too.
- **No PII leaves your infrastructure.** Evidence stays in Garage; the log stays in your Postgres. Sovereign by design.
- **Explainability preserved:** the `predicted` + `model_version` provenance makes every downstream model decision auditable back to its training basis.

---

## §WL1.9 — Failure modes & guards

| Failure | Guard |
|---|---|
| Redelivered event double-counts | `outcome_id` idempotency + `ON CONFLICT DO NOTHING` |
| Malformed source payload | Schema validate → DLQ (never a silent drop) |
| Late `deal.won` misattributed | `occurred_at` ordering; WL2 sorts by event time |
| Missing `predicted` block | Warn + log anyway; flag record as non-trainable for scoring |
| Garage evidence write fails | Store record with null evidence_ref + retry linker (record is never lost for lack of an artifact) |
| Bus outage | Consumer offsets/durable subscription → resume without gap |

---

## §WL1.10 — Import & configuration notes

- **Import:** n8n → Import from File → set credentials for the event bus (durable/wildcard subscription), Postgres, Neo4j, Garage (S3), Langfuse.
- **Env:** `OUTCOME_LOG_PARTITION` (monthly), `DLQ_TOPIC`, `EVIDENCE_BUCKET`, `SCHEMA_STRICT` (default true).
- **Build-order rule (non-negotiable):** deploy **WL1 first and immediately**, before any retrainer exists. Every week you aren't logging outcomes is training data you can never recover.
- **Companion workflows:** `FLOW-WL2` (attribution batch — multi-touch credit + Source Genome feed), `FLOW-WL3` (retrain cycle), `FLOW-WL4` (eval & shadow), `FLOW-WL5` (promotion & human approval), `FLOW-WL6` (drift watch).

---

## §WL1.11 — Elite differentiators

- **Learns from *no*.** Losses, no-shows, and disqualifications are first-class labels, not noise. Most systems only learn from deals that closed; this one learns from the ones that didn't.
- **Predicted-vs-actual captured at the source.** Logging the score *and its model version* at outcome time is what makes calibration and honest backtesting possible — most stacks lose this and can never reconstruct it.
- **Erasure that reaches the models.** Compliance isn't a database filter bolted on top — a forgotten prospect is purged from the training labels too.
- **Zero-loss by design.** Append-only, idempotent, DLQ-guarded. The ground truth for every future model is trustworthy because nothing is silently dropped or double-counted.

---

*Module `FLOW-WL1 v1.0` — the intake of the flywheel. Every other workflow now has a destination for its outcomes. With WG2 → W2 → WO1 → W5 → WV → **WL1**, the loop is closed: the system **finds → enriches → reaches → converses → books → hands off → and learns from the result.** Next executable link: `FLOW-WL2` (attribution batch) — turn logged outcomes into causal credit and the Source Genome update.*
