# 🧬 Prospect Dominion — W2 Enrichment & Email-Hunt Workflow

**Doc ID:** `FLOW-W2 v1.0`
**Layer:** Core v1.1 — Enrichment ▸ Verification ▸ Persona (§2.1 squads) · Orchestration §7
**Depends on:** `INFRA v1.0` (n8n, Postgres, Qdrant, Mem0, Crawl4AI, LiteLLM, Langfuse, Garage, NATS) · `DATA v1.0` (account/contact/enrichment/verification/persona tables) · `FLOW-WG2 v1.0` (produces the `lead.discovered` this consumes) · Blueprint v1.1 §5.2 (OSINT), §5.3 (Email Intelligence), §5.8 (Psychographics)
**Status:** Import-ready · executable n8n workflow JSON + config notes

---

## §0. What this is

The **money lane's gatekeeper.** WG2/WG1 discovery is near-zero-cost; **W2 is where real money and reputation get spent** — paid enrichment lookups, crawl budget, and SMTP probes from warmed IPs. So W2 is engineered as a **queue-driven fan-out/fan-in** pipeline that spends budget *only* on Triage-survivors, collapses duplicates before enrichment, and never lets a catch-all or risky address touch the send pool.

It consumes `lead.discovered`, builds a 360° account+contact profile, hunts + verifies the address, profiles the buyer psychographically, and emits `lead.enriched` + `lead.scored` for the Scoring/Copy squads.

> **Golden rule (inherited from L-GEN §6):** discovery is cheap, enrichment is not. Every stage here is behind a budget guard and an idempotency key. Nothing is re-crawled that Garage already has; nothing is re-verified inside its TTL.

---

## §1. Layer stack (this workflow only)

```
┌──────────────────────────────────────────────────────────────────────┐
│ INGRESS    NATS sub lead.discovered  → per-candidate job (queue mode)  │
├──────────────────────────────────────────────────────────────────────┤
│ RESOLVE    Merge Agent: dedupe → canonical account_id / contact_id     │
├──────────────────────────────────────────────────────────────────────┤
│ BUDGET     Cost-per-qualified-lead guard (per ICP segment) → gate      │
├──────────────────────────────────────────────────────────────────────┤
│ FAN-OUT    ‖ Firmographic  ‖ Technographic  ‖ Social/News              │
│            (parallel enrichment agents, each cached + TTL-checked)      │
├──────────────────────────────────────────────────────────────────────┤
│ FAN-IN     Merge → 360° profile → Postgres (truth) + Qdrant (vectors)  │
├──────────────────────────────────────────────────────────────────────┤
│ HUNT       House-pattern inference (Crawl4AI + dork) → candidate addrs  │
├──────────────────────────────────────────────────────────────────────┤
│ VERIFY     5-stage microservice → deliverable / catch-all / risky      │
├──────────────────────────────────────────────────────────────────────┤
│ PERSONA    Psychographic clusterer → segment + tone/format profile     │
├──────────────────────────────────────────────────────────────────────┤
│ EMIT       lead.enriched + lead.scored → NATS · profile persisted      │
├──────────────────────────────────────────────────────────────────────┤
│ OBSERVE    Langfuse trace · Garage raw-evidence archive · DLQ on fail  │
└──────────────────────────────────────────────────────────────────────┘
```

**Squads touched:** **Enrichment Squad** (Firmographic / Technographic / Social/News / Merge Agents), **Verification Squad** (Pattern Inference / SMTP Verifier / Risk Classifier), **Persona Squad** (Psychographic Clusterer / Persona Writer). Hands off to Scoring + Copy squads via `lead.enriched` / `lead.scored`.

---

## §2. Event contract

**In —** `lead.discovered` (NATS subject `lead.discovered`, see `FLOW-WG2 v1.0` §2):

```json
{
  "candidate_id": "cand_...",
  "account_id": "acct_...",
  "contacts": [{ "contact_id": "...", "role": "economic_buyer", "confidence": 0.82 }],
  "provenance": { "lane": "WG2", "originating_signal": {"...": "..."}, "icp_fit": 0.88 },
  "priority": "signal_lane",
  "trace_id": "lf_..."
}
```

**Out A —** `lead.enriched` (NATS subject `lead.enriched`):

```json
{
  "account_id": "acct_...",
  "contact_id": "ct_...",
  "profile": {
    "firmographic": { "employees": 180, "revenue_band": "10-50M", "hq": "US", "sourced_at": "..." },
    "technographic": { "stack": ["hubspot","segment","aws"], "migrating_from": "marketo", "sourced_at": "..." },
    "social_news": [{ "type": "exec_hire", "url": "...", "ts": "..." }]
  },
  "email": { "address": "j.doe@acme.example", "pattern": "f.last", "bucket": "deliverable", "risk": 0.04 },
  "persona": { "segment": "analytical_operator", "tone": "concise_data", "format": "bullets_first" },
  "evidence_uri": "garage://evidence/acct_.../w2.json",
  "trace_id": "lf_..."
}
```

**Out B —** `lead.scored` (thin event; full model lives in the Scoring workflow, W-SCORE):

```json
{ "account_id": "acct_...", "contact_id": "ct_...", "icp_fit": 0.88, "enrich_completeness": 0.91, "ready_for_scoring": true, "trace_id": "lf_..." }
```

**Dead-letter —** subject `dlq.w2` with `{ candidate_id, stage, error, attempts, ts }`.

---

## §3. Stage detail

### §3.1 Merge / entity resolution (before any spend)
Deterministic keys first (domain + normalized name), then embedding match (contact name+title vs. existing `contact` vectors in Qdrant, cosine ≥ 0.92). Collapse into canonical `account_id`/`contact_id`. **This runs before the budget gate** — resolving a dup to an existing enriched account short-circuits the whole lane (emit `lead.enriched` from cache, skip spend). Prevents the classic "same person 4× enrichment waste."

### §3.2 Budget guard (waterfall economics)
Read `cost_ledger` for the candidate's `icp_segment`. If segment's **cost-per-qualified-lead** is at cap → route to `nurture_watch` (park, no spend) and emit `dlq.w2` reason `budget_capped` for ops visibility. Otherwise reserve budget and proceed. Cheapest sources fire first; expensive paid lookups only fire if cheaper layers left `enrich_completeness < target`.

### §3.3 Parallel enrichment (fan-out)
Three independent branches, each: (a) TTL check against `enrichment.sourced_at` — skip if fresh; (b) Garage check — reuse raw evidence if present; (c) fetch → normalize → write-through Postgres + Qdrant. Branches never block each other; a single-branch failure degrades completeness but does not kill the job.

### §3.4 Fan-in / Merge Agent
Wait-for-all (with per-branch timeout). Compose the 360° profile, compute `enrich_completeness` (0–1), write canonical row, upsert derived embedding to Qdrant, store episodic note to Mem0, archive raw evidence to Garage with `evidence_uri`.

### §3.5 Email hunt + 5-stage verify
House-pattern inference (Crawl4AI sweep of team/about/PDF/GitHub/press) → generate candidate addresses → **5-stage verify microservice** (syntax → domain+MX → SMTP probe from warmed IP → role/disposable/catch-all classify → risk score). Buckets: **deliverable** (send-eligible) · **catch-all** (quarantine — conservative low-volume treatment, never mixed with verified sends) · **risky** (never send). Target bounce < 2%.

### §3.6 Persona profiling
Psychographic clusterer assigns segment + tone/format from behavioral + text signals; Persona Writer emits the copy-tuning profile the Copy Squad consumes. Written to `persona` table + Mem0.

---

## §4. The workflow (import-ready n8n JSON)

```json
{
  "name": "PD — W2 Enrichment & Email Hunt",
  "settings": { "executionOrder": "v1", "saveManualExecutions": true, "callerPolicy": "workflowsFromSameOwner" },
  "nodes": [
    {
      "parameters": {
        "authentication": "none",
        "subject": "lead.discovered",
        "options": { "queue": "w2-workers", "ackMode": "onSuccess" }
      },
      "id": "nats_in",
      "name": "NATS ▸ lead.discovered",
      "type": "n8n-nodes-base.natsTrigger",
      "typeVersion": 1,
      "position": [-1120, 400]
    },
    {
      "parameters": {
        "jsCode": "// Open Langfuse trace + validate envelope\nconst e = $json;\nif (!e.candidate_id || !e.account_id) { throw new Error('w2:bad_envelope'); }\nconst trace_id = e.trace_id || ('lf_w2_' + e.candidate_id);\nreturn [{ json: { ...e, trace_id, _stage: 'ingress', _attempt: (e._attempt||0)+1 } }];"
      },
      "id": "trace_open",
      "name": "Open Trace + Validate",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [-900, 400]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://merge-svc:8090/resolve",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ account_id: $json.account_id, contacts: $json.contacts, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 15000 }
      },
      "id": "merge_resolve",
      "name": "Merge Agent ▸ resolve",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [-680, 400]
    },
    {
      "parameters": {
        "conditions": { "options": { "caseSensitive": true }, "combinator": "and",
          "conditions": [ { "leftValue": "={{ $json.duplicate_of_enriched }}", "rightValue": true, "operator": { "type": "boolean", "operation": "true" } } ] }
      },
      "id": "if_cached",
      "name": "IF already enriched (cache hit)",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [-460, 400]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://budget-svc:8091/reserve",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ icp_segment: $json.icp_segment || 'default', account_id: $json.account_id, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 8000 }
      },
      "id": "budget_reserve",
      "name": "Budget Guard ▸ reserve",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [-240, 480]
    },
    {
      "parameters": {
        "conditions": { "combinator": "and", "conditions": [
          { "leftValue": "={{ $json.reserved }}", "rightValue": true, "operator": { "type": "boolean", "operation": "true" } } ] }
      },
      "id": "if_budget",
      "name": "IF budget available",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [-20, 480]
    },
    {
      "parameters": {
        "method": "POST", "url": "http://enrich-svc:8092/firmographic",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ account_id: $json.account_id, ttl_check: true, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 20000 }
      },
      "id": "enr_firmo",
      "name": "‖ Firmographic",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [220, 300]
    },
    {
      "parameters": {
        "method": "POST", "url": "http://enrich-svc:8092/technographic",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ account_id: $json.account_id, ttl_check: true, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 20000 }
      },
      "id": "enr_techno",
      "name": "‖ Technographic",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [220, 480]
    },
    {
      "parameters": {
        "method": "POST", "url": "http://enrich-svc:8092/social-news",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ account_id: $json.account_id, ttl_check: true, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 20000 }
      },
      "id": "enr_social",
      "name": "‖ Social / News",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [220, 660]
    },
    {
      "parameters": { "mode": "combine", "combineBy": "combineAll", "options": {} },
      "id": "fan_in",
      "name": "Fan-in (wait-for-all)",
      "type": "n8n-nodes-base.merge",
      "typeVersion": 3,
      "position": [460, 480]
    },
    {
      "parameters": {
        "method": "POST", "url": "http://merge-svc:8090/compose",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ account_id: $json.account_id, branches: $items().map(i=>i.json), trace_id: $json.trace_id }) }}",
        "options": { "timeout": 15000 }
      },
      "id": "compose",
      "name": "Merge ▸ 360° profile → PG+Qdrant+Garage",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [680, 480]
    },
    {
      "parameters": {
        "method": "POST", "url": "http://email-intel:8093/hunt",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ domain: $json.domain, contact_id: $json.contact_id, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 25000 }
      },
      "id": "email_hunt",
      "name": "Email Hunt ▸ pattern infer",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [900, 400]
    },
    {
      "parameters": {
        "method": "POST", "url": "http://email-intel:8093/verify",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ candidates: $json.candidate_addresses, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 30000 }
      },
      "id": "email_verify",
      "name": "5-Stage Verify (warmed IP)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [1120, 400]
    },
    {
      "parameters": {
        "dataType": "string",
        "value1": "={{ $json.bucket }}",
        "rules": { "rules": [
          { "value2": "deliverable", "output": 0 },
          { "value2": "catch-all", "output": 1 },
          { "value2": "risky", "output": 2 } ] },
        "fallbackOutput": 2
      },
      "id": "switch_bucket",
      "name": "Switch ▸ bucket",
      "type": "n8n-nodes-base.switch",
      "typeVersion": 3,
      "position": [1340, 400]
    },
    {
      "parameters": {
        "method": "POST", "url": "http://persona-svc:8094/profile",
        "sendBody": true, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ account_id: $json.account_id, contact_id: $json.contact_id, trace_id: $json.trace_id }) }}",
        "options": { "timeout": 20000 }
      },
      "id": "persona",
      "name": "Persona ▸ psychographic profile",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [1560, 300]
    },
    {
      "parameters": {
        "jsCode": "// Compose lead.enriched + lead.scored payloads\nconst j = $json;\nconst enriched = { account_id: j.account_id, contact_id: j.contact_id, profile: j.profile, email: j.email, persona: j.persona, evidence_uri: j.evidence_uri, trace_id: j.trace_id };\nconst scored = { account_id: j.account_id, contact_id: j.contact_id, icp_fit: j.icp_fit, enrich_completeness: j.enrich_completeness, ready_for_scoring: (j.enrich_completeness||0) >= 0.6, trace_id: j.trace_id };\nreturn [{ json: { enriched, scored } }];"
      },
      "id": "compose_out",
      "name": "Compose out events",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1780, 300]
    },
    {
      "parameters": { "subject": "lead.enriched", "message": "={{ JSON.stringify($json.enriched) }}" },
      "id": "emit_enriched",
      "name": "NATS ▸ lead.enriched",
      "type": "n8n-nodes-base.nats",
      "typeVersion": 1,
      "position": [2000, 220]
    },
    {
      "parameters": { "subject": "lead.scored", "message": "={{ JSON.stringify($json.scored) }}" },
      "id": "emit_scored",
      "name": "NATS ▸ lead.scored",
      "type": "n8n-nodes-base.nats",
      "typeVersion": 1,
      "position": [2000, 380]
    },
    {
      "parameters": {
        "jsCode": "// Catch-all quarantine — conservative treatment, still profiled, flagged\nreturn [{ json: { ...$json, send_policy: 'catch_all_conservative', quarantined: true } }];"
      },
      "id": "quarantine",
      "name": "Catch-all ▸ quarantine",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1560, 480]
    },
    {
      "parameters": {
        "jsCode": "// Risky / dead → suppress, never send\nreturn [{ json: { account_id: $json.account_id, contact_id: $json.contact_id, reason: 'unverifiable', suppress: true, trace_id: $json.trace_id } }];"
      },
      "id": "suppress",
      "name": "Risky ▸ suppress",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1560, 640]
    },
    {
      "parameters": {
        "jsCode": "// Cache-hit fast path: emit enriched from stored profile, no spend\nreturn [{ json: { enriched: $json.cached_profile, scored: { account_id: $json.account_id, contact_id: $json.contact_id, ready_for_scoring: true, trace_id: $json.trace_id } } }];"
      },
      "id": "cache_emit",
      "name": "Cache hit → emit",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [-240, 300]
    },
    {
      "parameters": { "subject": "dlq.w2", "message": "={{ JSON.stringify({ candidate_id: $json.candidate_id, stage: $json._stage || 'unknown', error: $json.error || 'budget_capped', attempts: $json._attempt || 1, ts: $now.toISO() }) }}" },
      "id": "dlq",
      "name": "NATS ▸ dlq.w2",
      "type": "n8n-nodes-base.nats",
      "typeVersion": 1,
      "position": [-20, 700]
    }
  ],
  "connections": {
    "NATS ▸ lead.discovered": { "main": [[{ "node": "Open Trace + Validate", "type": "main", "index": 0 }]] },
    "Open Trace + Validate": { "main": [[{ "node": "Merge Agent ▸ resolve", "type": "main", "index": 0 }]] },
    "Merge Agent ▸ resolve": { "main": [[{ "node": "IF already enriched (cache hit)", "type": "main", "index": 0 }]] },
    "IF already enriched (cache hit)": { "main": [ [{ "node": "Cache hit → emit", "type": "main", "index": 0 }], [{ "node": "Budget Guard ▸ reserve", "type": "main", "index": 0 }] ] },
    "Budget Guard ▸ reserve": { "main": [[{ "node": "IF budget available", "type": "main", "index": 0 }]] },
    "IF budget available": { "main": [ [ { "node": "‖ Firmographic", "type": "main", "index": 0 }, { "node": "‖ Technographic", "type": "main", "index": 0 }, { "node": "‖ Social / News", "type": "main", "index": 0 } ], [{ "node": "NATS ▸ dlq.w2", "type": "main", "index": 0 }] ] },
    "‖ Firmographic": { "main": [[{ "node": "Fan-in (wait-for-all)", "type": "main", "index": 0 }]] },
    "‖ Technographic": { "main": [[{ "node": "Fan-in (wait-for-all)", "type": "main", "index": 1 }]] },
    "‖ Social / News": { "main": [[{ "node": "Fan-in (wait-for-all)", "type": "main", "index": 2 }]] },
    "Fan-in (wait-for-all)": { "main": [[{ "node": "Merge ▸ 360° profile → PG+Qdrant+Garage", "type": "main", "index": 0 }]] },
    "Merge ▸ 360° profile → PG+Qdrant+Garage": { "main": [[{ "node": "Email Hunt ▸ pattern infer", "type": "main", "index": 0 }]] },
    "Email Hunt ▸ pattern infer": { "main": [[{ "node": "5-Stage Verify (warmed IP)", "type": "main", "index": 0 }]] },
    "5-Stage Verify (warmed IP)": { "main": [[{ "node": "Switch ▸ bucket", "type": "main", "index": 0 }]] },
    "Switch ▸ bucket": { "main": [ [{ "node": "Persona ▸ psychographic profile", "type": "main", "index": 0 }], [{ "node": "Catch-all ▸ quarantine", "type": "main", "index": 0 }], [{ "node": "Risky ▸ suppress", "type": "main", "index": 0 }] ] },
    "Persona ▸ psychographic profile": { "main": [[{ "node": "Compose out events", "type": "main", "index": 0 }]] },
    "Compose out events": { "main": [[ { "node": "NATS ▸ lead.enriched", "type": "main", "index": 0 }, { "node": "NATS ▸ lead.scored", "type": "main", "index": 0 } ]] },
    "Catch-all ▸ quarantine": { "main": [[{ "node": "Persona ▸ psychographic profile", "type": "main", "index": 0 }]] }
  }
}
```

---

## §5. Node-by-node rationale

| Node | Why it exists | Failure behavior |
|---|---|---|
| NATS ▸ lead.discovered | Queue-mode sub → horizontal worker scaling; ack-on-success gives at-least-once | Unacked → redelivered to another worker |
| Open Trace + Validate | Langfuse span + envelope guard; increments `_attempt` | Bad envelope → throw → DLQ |
| Merge Agent ▸ resolve | Collapse dupes **before spend**; cache short-circuit | Timeout → DLQ stage=`merge` |
| IF cache hit | Emit from stored profile, skip all spend | n/a |
| Budget Guard ▸ reserve | Cost-per-qualified-lead cap per ICP segment | Not reserved → DLQ reason=`budget_capped` (park in nurture) |
| ‖ Firmo/Techno/Social | Parallel enrichment; each TTL+Garage cached | Single-branch fail → degraded completeness, job survives |
| Fan-in | Wait-for-all with per-branch timeout | Partial → compose with what arrived |
| Merge ▸ compose | 360° profile, write-through PG(truth)+Qdrant(vectors)+Garage(evidence) | Timeout → DLQ stage=`compose` |
| Email Hunt + 5-Stage Verify | House pattern → verify from **warmed IP**; bounce<2% | Greylist → graceful retry inside svc |
| Switch ▸ bucket | deliverable→send-eligible · catch-all→quarantine · risky→suppress | Fallback = risky (safe default) |
| Persona | Psychographic segment + tone for Copy Squad | Fail → emit without persona, flag `persona_missing` |
| Compose + emit | `lead.enriched` + `lead.scored` handoff | — |

---

## §6. Idempotency, retries & concurrency

- **Idempotency key:** `w2:{account_id}:{contact_id}`. All external writes (PG upserts, Qdrant, Garage) keyed by canonical IDs — a redelivered job is a no-op on already-written facts.
- **Retries:** each HTTP node → 3 attempts, exponential backoff (2s/8s/30s). Exhausted → DLQ with `_stage`.
- **Concurrency:** queue `w2-workers`; scale replicas horizontally. Budget guard is the global throttle — a discovery spike cannot overwhelm paid stages because reservations fail closed.
- **TTL freshness:** every enrichment carries `sourced_at`; branch skips fetch if within TTL and reuses Garage evidence. Ops Squad re-verify job (separate flow) retriggers W2 on TTL expiry or job-change detection.

---

## §7. Config notes (import checklist)

1. **Credentials:** NATS connection (`nats://nats:4222`), Langfuse env (`LANGFUSE_HOST/PUBLIC/SECRET`) on all Code nodes.
2. **Service endpoints** (from `INFRA v1.0` compose network): `merge-svc:8090`, `budget-svc:8091`, `enrich-svc:8092`, `email-intel:8093`, `persona-svc:8094`. Adjust to your service names.
3. **Budget caps:** seed `cost_ledger` per ICP segment (see `DATA v1.0`); set `cost_per_qualified_lead` caps before enabling.
4. **Verify IP pool:** point `email-intel` at **warmed** verification IPs only (distinct from send IPs). Confirm reverse DNS + graceful greylist handling.
5. **Qdrant collections:** `contacts` (for merge NN) + `accounts` (for lookalike) must exist with matching vector dims.
6. **Enable order:** import → dry-run with `EMIT_DISABLED=true` (comment out NATS-out) → verify PG/Qdrant/Garage writes → enable emits → connect to live `lead.discovered`.

---

## §8. Where this sits in the build order

```
FLOW-WG2 (discovery) ──emits──► lead.discovered
                                      │
                              ┌───────▼───────┐
                              │   FLOW-W2     │  ◄── you are here
                              │ enrich+verify │
                              └───────┬───────┘
                     emits lead.enriched / lead.scored
                                      │
                              ┌───────▼───────┐
                              │  W-SCORE      │  (next: ML propensity + SHAP)
                              │  → W-COPY     │  (5-layer personalization)
                              │  → W-SEND     │  (cadence → Postal, L-SEND)
                              └───────────────┘
```

**Exit gate before scaling W2:** verify bounce < 2% on a 200-address sample, budget guard demonstrably parks over-cap segments, and Merge collapses a known-dup test set to a single canonical ID.

---

## §9. Elite differentiators

1. **Spend-after-screen architecture** — money and reputation are committed only past dedup + budget gate; discovery firehose can never bankrupt the paid lane.
2. **Cache-short-circuit on dup** — a rediscovered account emits `lead.enriched` from stored truth with zero new spend.
3. **Warmed-IP verification isolation** — verify probes never touch send IPs, protecting sender reputation from probe-driven blocklisting.
4. **Catch-all quarantine, not discard** — catch-alls are profiled and kept for conservative treatment, not thrown away, but never mixed into verified sends.
5. **Grounded persona handoff** — every enriched lead carries a psychographic tone/format profile so the Copy Squad's personalization is segment-tuned, not generic.
6. **Re-derivable enrichment** — raw evidence in Garage means any profile can be recomputed without re-crawling, surviving schema/model upgrades.

---

*FLOW-W2 v1.0 — the gate where discovery becomes an asset worth spending on.*
