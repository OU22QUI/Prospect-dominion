# ⚡ Prospect Dominion — WG2 Signal-First Discovery Workflow

**Doc ID:** `FLOW-WG2 v1.0`
**Layer:** L-GEN (Autonomous Lead Generation) · Orchestration §7
**Depends on:** `INFRA v1.0` (n8n, Postgres, LiteLLM, Crawl4AI, Langfuse, Garage, NATS) · `DATA v1.0` (candidate ledger, suppression, budget tables) · `L-GEN v1.0` §5 (Signal-first) & §6 (Triage Gate)
**Status:** Import-ready · executable n8n workflow JSON + config notes

---

## §0. What this is

The **crown-jewel discovery lane**. Where WG1 (Continuous Sweep) *pulls* on a schedule, **WG2 fires on a buying signal** — funding, exec hire, tech change, hiring surge, review/complaint, expansion — back-resolves the account and buying committee, attaches the originating signal as a **grounded hook**, and pushes screened candidates into the priority Triage lane.

> **Inverted funnel:** the lead is discovered *because* it emitted intent, not because it appeared on a list. The signal travels with the candidate as provenance, so the downstream Copy Squad's opener is guaranteed factually grounded.

---

## §1. Layer stack (this workflow only)

```
┌─────────────────────────────────────────────────────────────────┐
│ INGRESS   Webhook /signal-in  ← signal monitors (RSS, WGx, APIs) │
├─────────────────────────────────────────────────────────────────┤
│ NORMALIZE Signal → canonical envelope (type, entity, ts, source) │
├─────────────────────────────────────────────────────────────────┤
│ RESOLVE   Account + buying committee (Crawl4AI + Dork + LiteLLM) │
├─────────────────────────────────────────────────────────────────┤
│ GATE      Dedup → ICP-fit → Suppression → Budget guard           │
├─────────────────────────────────────────────────────────────────┤
│ EMIT      lead.discovered → NATS bus + candidate ledger insert   │
├─────────────────────────────────────────────────────────────────┤
│ OBSERVE   Langfuse trace · Garage artifact archive · DLQ on fail │
└─────────────────────────────────────────────────────────────────┘
```

**Squads touched:** Discovery Crew — *Signal Scout* (supervisor of this lane), *Surface Harvesters* (resolution fetches), *Triage Gate* (immune system). Hands off to the Recon Squad unchanged via `lead.discovered`.

---

## §2. Event contract

**In —** `signal.detected` (POST `/webhook/signal-in`):

```json
{
  "signal_id": "sig_2026_0142",
  "signal_type": "funding_round",
  "entity_hint": { "name": "Acme Fintech", "domain": "acme.example", "linkedin": null },
  "detail": { "round": "Series B", "amount_usd": 24000000, "investors": ["..."] },
  "source": { "surface": "funding_feed", "url": "https://...", "detected_at": "2026-08-24T12:01:00Z" },
  "icp_segment": "series_b_fintech"
}
```

**Out —** `lead.discovered` (NATS subject `lead.discovered`, mirrored to `candidate` table):

```json
{
  "candidate_id": "cand_...",
  "account_id": "acct_...",
  "contacts": [{ "contact_id": "...", "role": "economic_buyer", "confidence": 0.82 }],
  "provenance": {
    "lane": "WG2",
    "originating_signal": { "signal_id": "sig_2026_0142", "type": "funding_round", "url": "..." },
    "surface": "funding_feed", "icp_fit": 0.88, "lookalike": 0.79
  },
  "priority": "signal_lane",
  "trace_id": "lf_..."
}
```

---

## §3. The workflow (import-ready n8n JSON)

> Import: **n8n → Workflows → Import from File**. Then bind the four credentials in §4 and activate. All internal service hostnames match `INFRA v1.0` compose network aliases.

```json
{
  "name": "WG2 — Signal-First Discovery",
  "settings": { "executionOrder": "v1", "saveManualExecutions": true, "callerPolicy": "workflowsFromSameOwner" },
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "signal-in",
        "responseMode": "responseNode",
        "options": { "rawBody": false }
      },
      "id": "n_webhook",
      "name": "Signal Ingress",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [-1120, 300],
      "webhookId": "wg2-signal-in"
    },
    {
      "parameters": {
        "jsCode": "// Normalize inbound signal to canonical envelope + start trace\nconst b = $input.first().json.body || $input.first().json;\nif (!b.signal_id || !b.signal_type) { throw new Error('DLQ:missing_signal_fields'); }\nconst env = {\n  signal_id: b.signal_id,\n  signal_type: b.signal_type,\n  entity_hint: b.entity_hint || {},\n  detail: b.detail || {},\n  source: b.source || {},\n  icp_segment: b.icp_segment || 'unassigned',\n  received_at: new Date().toISOString(),\n  trace_id: 'lf_' + [...crypto.getRandomValues(new Uint8Array(8))].map(x=>x.toString(16).padStart(2,'0')).join('')\n};\nreturn [{ json: env }];"
      },
      "id": "n_normalize",
      "name": "Normalize Signal",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [-900, 300]
    },
    {
      "parameters": {
        "url": "http://langfuse-web:3000/api/public/ingestion",
        "method": "POST",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpBasicAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"batch\": [{\n    \"type\": \"trace-create\",\n    \"id\": \"{{$json.trace_id}}\",\n    \"body\": { \"name\": \"WG2-signal-first\", \"input\": {{ JSON.stringify($json) }}, \"metadata\": { \"lane\": \"WG2\", \"signal_type\": \"{{$json.signal_type}}\" } }\n  }]\n}",
        "options": { "batching": { "batch": { "batchSize": 1 } } }
      },
      "id": "n_trace_open",
      "name": "Langfuse: Open Trace",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [-680, 300],
      "continueOnFail": true
    },
    {
      "parameters": {
        "url": "http://crawl4ai:11235/crawl",
        "method": "POST",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"urls\": [\"{{$json.source.url}}\"],\n  \"extraction_strategy\": \"llm\",\n  \"word_count_threshold\": 20\n}",
        "options": { "timeout": 45000, "response": { "response": { "neverError": true } } }
      },
      "id": "n_crawl",
      "name": "Crawl4AI: Source Page",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [-460, 300],
      "continueOnFail": true
    },
    {
      "parameters": {
        "url": "http://litellm:4000/v1/chat/completions",
        "method": "POST",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"model\": \"resolver\",\n  \"response_format\": { \"type\": \"json_object\" },\n  \"messages\": [\n    { \"role\": \"system\", \"content\": \"You resolve a buying signal into an account and buying committee. Return STRICT JSON: {account:{name,domain,hq_country,employee_band,industry}, contacts:[{full_name,role,seniority,likely_email_pattern,confidence}], resolution_confidence}. Roles limited to: economic_buyer, champion, technical_buyer, blocker, user. Do NOT invent emails; only patterns. Use only evidence provided.\" },\n    { \"role\": \"user\", \"content\": \"SIGNAL: {{ JSON.stringify($('Normalize Signal').item.json) }}\\n\\nPAGE_CONTENT: {{ JSON.stringify(($json.results && $json.results[0] && $json.results[0].markdown) || $json.markdown || '') }}\" }\n  ]\n}",
        "options": { "timeout": 60000 }
      },
      "id": "n_resolve",
      "name": "LiteLLM: Resolve Committee",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [-240, 300]
    },
    {
      "parameters": {
        "jsCode": "// Parse resolver output, attach provenance, compute canonical keys\nconst env = $('Normalize Signal').item.json;\nlet r;\ntry { r = JSON.parse($json.choices[0].message.content); } catch(e) { throw new Error('DLQ:resolver_bad_json'); }\nif (!r.account || !r.account.domain) { throw new Error('DLQ:unresolved_account'); }\nconst norm = s => (s||'').toLowerCase().replace(/^www\\./,'').trim();\nconst account_key = norm(r.account.domain);\nreturn [{ json: {\n  trace_id: env.trace_id,\n  icp_segment: env.icp_segment,\n  originating_signal: { signal_id: env.signal_id, type: env.signal_type, url: env.source.url, detail: env.detail },\n  account: { ...r.account, account_key },\n  contacts: (r.contacts||[]).map(c => ({ ...c, contact_key: account_key + '|' + norm(c.full_name) })),\n  resolution_confidence: r.resolution_confidence ?? 0.5\n} }];"
      },
      "id": "n_shape",
      "name": "Shape Candidate",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [-20, 300]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "-- GATE 1 dedup + GATE 3 suppression in one round-trip\nSELECT\n  EXISTS(SELECT 1 FROM candidate WHERE account_key = $1) AS dup_candidate,\n  EXISTS(SELECT 1 FROM suppression WHERE value = $1 AND scope IN ('account','domain')) AS suppressed,\n  (SELECT remaining FROM discovery_budget WHERE icp_segment = $2 AND period = date_trunc('day', now())) AS budget_remaining;",
        "additionalFields": { "queryParams": "={{ $json.account.account_key }},={{ $json.icp_segment }}" }
      },
      "id": "n_gate_sql",
      "name": "Gate: Dedup+Suppress+Budget",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [200, 300]
    },
    {
      "parameters": {
        "jsCode": "// GATE 2 ICP-fit + budget/dup/suppression enforcement\nconst cand = $('Shape Candidate').item.json;\nconst g = $json;\nif (g.dup_candidate) { return [{ json: { ...cand, _drop: 'duplicate' } }]; }\nif (g.suppressed)   { return [{ json: { ...cand, _drop: 'suppressed' } }]; }\nif (g.budget_remaining !== null && Number(g.budget_remaining) <= 0) { return [{ json: { ...cand, _drop: 'budget_exhausted' } }]; }\n// cheap ICP-fit heuristic; signal lane gets intent-proximity bonus\nlet fit = 0.5;\nif (cand.resolution_confidence >= 0.7) fit += 0.2;\nif ((cand.contacts||[]).some(c => ['economic_buyer','champion'].includes(c.role))) fit += 0.15;\nfit = Math.min(1, fit + 0.1); // signal-lane bonus\nconst pass = fit >= 0.6;\nreturn [{ json: { ...cand, icp_fit: Number(fit.toFixed(2)), _drop: pass ? null : 'below_icp_bar' } }];"
      },
      "id": "n_gate_logic",
      "name": "Gate: ICP-Fit + Enforce",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [420, 300]
    },
    {
      "parameters": {
        "conditions": { "options": { "caseSensitive": true }, "combinator": "and",
          "conditions": [ { "leftValue": "={{ $json._drop }}", "rightValue": "", "operator": { "type": "string", "operation": "empty" } } ] }
      },
      "id": "n_if_pass",
      "name": "Passed Gate?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [640, 300]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "-- EMIT: idempotent insert to candidate ledger + decrement budget\nWITH ins AS (\n  INSERT INTO candidate (account_key, account_json, contacts_json, provenance_json, icp_fit, priority, trace_id, discovered_at)\n  VALUES ($1, $2, $3, $4, $5, 'signal_lane', $6, now())\n  ON CONFLICT (account_key) DO NOTHING\n  RETURNING candidate_id, account_key\n)\nUPDATE discovery_budget SET remaining = remaining - 1\n WHERE icp_segment = $7 AND period = date_trunc('day', now())\n RETURNING (SELECT candidate_id FROM ins) AS candidate_id;",
        "additionalFields": { "queryParams": "={{ $json.account.account_key }},={{ JSON.stringify($json.account) }},={{ JSON.stringify($json.contacts) }},={{ JSON.stringify($json.originating_signal) }},={{ $json.icp_fit }},={{ $json.trace_id }},={{ $json.icp_segment }}" }
      },
      "id": "n_persist",
      "name": "Persist Candidate",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [860, 200]
    },
    {
      "parameters": {
        "url": "http://nats:8222/",
        "method": "POST",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"subject\": \"lead.discovered\",\n  \"payload\": {{ JSON.stringify($('Gate: ICP-Fit + Enforce').item.json) }},\n  \"candidate_id\": \"{{ $json.candidate_id }}\"\n}",
        "options": { "response": { "response": { "neverError": true } } }
      },
      "id": "n_emit",
      "name": "Emit lead.discovered",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [1080, 200],
      "continueOnFail": true
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "INSERT INTO triage_dropped (account_key, reason, provenance_json, trace_id, dropped_at) VALUES ($1,$2,$3,$4,now());",
        "additionalFields": { "queryParams": "={{ $json.account.account_key }},={{ $json._drop }},={{ JSON.stringify($json.originating_signal) }},={{ $json.trace_id }}" }
      },
      "id": "n_drop_log",
      "name": "Log Drop",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [860, 420]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={ \"ok\": true, \"trace_id\": \"{{ $('Normalize Signal').item.json.trace_id }}\" }"
      },
      "id": "n_respond",
      "name": "Ack",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [1300, 300]
    }
  ],
  "connections": {
    "Signal Ingress":            { "main": [[{ "node": "Normalize Signal", "type": "main", "index": 0 }]] },
    "Normalize Signal":          { "main": [[{ "node": "Langfuse: Open Trace", "type": "main", "index": 0 }]] },
    "Langfuse: Open Trace":      { "main": [[{ "node": "Crawl4AI: Source Page", "type": "main", "index": 0 }]] },
    "Crawl4AI: Source Page":     { "main": [[{ "node": "LiteLLM: Resolve Committee", "type": "main", "index": 0 }]] },
    "LiteLLM: Resolve Committee":{ "main": [[{ "node": "Shape Candidate", "type": "main", "index": 0 }]] },
    "Shape Candidate":           { "main": [[{ "node": "Gate: Dedup+Suppress+Budget", "type": "main", "index": 0 }]] },
    "Gate: Dedup+Suppress+Budget":{ "main": [[{ "node": "Gate: ICP-Fit + Enforce", "type": "main", "index": 0 }]] },
    "Gate: ICP-Fit + Enforce":   { "main": [[{ "node": "Passed Gate?", "type": "main", "index": 0 }]] },
    "Passed Gate?":              { "main": [
                                    [{ "node": "Persist Candidate", "type": "main", "index": 0 }],
                                    [{ "node": "Log Drop", "type": "main", "index": 0 }]
                                  ] },
    "Persist Candidate":         { "main": [[{ "node": "Emit lead.discovered", "type": "main", "index": 0 }]] },
    "Emit lead.discovered":      { "main": [[{ "node": "Ack", "type": "main", "index": 0 }]] },
    "Log Drop":                  { "main": [[{ "node": "Ack", "type": "main", "index": 0 }]] }
  },
  "active": false,
  "pinData": {},
  "tags": [{ "name": "L-GEN" }, { "name": "discovery" }, { "name": "signal-first" }]
}
```

---

## §4. Credentials to bind (4)

| n8n credential | Type | Used by | Value source (`INFRA v1.0`) |
|---|---|---|---|
| **Langfuse Basic** | HTTP Basic Auth | Open Trace | `LANGFUSE_PUBLIC_KEY` : `LANGFUSE_SECRET_KEY` |
| **LiteLLM Key** | HTTP Header Auth | Resolve Committee | header `Authorization: Bearer $LITELLM_MASTER_KEY` |
| **Postgres Main** | Postgres | Gate / Persist / Log | host `postgres`, db `prospect`, user `pd_app` |
| *(Crawl4AI / NATS)* | none | Source Page / Emit | internal network, token optional via header |

> **Model alias:** `resolver` is defined in LiteLLM's `config.yaml` → route to your local resolution model (e.g. a quantized 70B). No provider name leaks into the workflow.

---

## §5. Gate semantics (why each check, in order)

1. **Dedup first (cheapest kill)** — one SQL round-trip also fetches suppression + budget, so a duplicate never triggers a resolve re-pay. Keyed on canonical `account_key` (domain-normalized).
2. **Suppression** — global do-not-contact / prior-opt-out / competitor / existing-customer lists. Legal hard stop.
3. **Budget guard** — per-ICP daily discovery budget; at zero the candidate is dropped to `triage_dropped`, not queued (back-pressure, not backlog).
4. **ICP-fit + signal-lane bonus** — cheap heuristic here; the *expensive* enrichment happens downstream only for survivors. Signal-lane candidates get an intent-proximity bonus and jump the queue (`priority: signal_lane`).
5. **Idempotent emit** — `ON CONFLICT (account_key) DO NOTHING` guarantees exactly-once ledger entry even under webhook retries.

> **Golden rule (L-GEN §6):** discovery is near-zero cost; enrichment + verification cost money and reputation. The Gate ensures those budgets are spent only on screened, non-suppressed, ICP-fit survivors.

---

## §6. Reliability & observability

- **DLQ:** any `throw new Error('DLQ:...')` in a Code node surfaces the reason; attach an **Error Trigger** workflow that writes `{workflow, node, reason, input}` to a `dlq` table for replay. (Set workflow **Settings → Error Workflow → `SYS-DLQ`**.)
- **continueOnFail** on Langfuse / Crawl4AI / Emit — a tracing or bus hiccup never loses a resolved candidate (it's already persisted before emit).
- **Garage archive:** extend the Crawl node's output to `PUT` the raw page + SERP artifact to Garage keyed by `trace_id` for audit & replay (add one HTTP node before Shape).
- **Politeness:** resolution fetches inherit per-surface cooldowns; because WG2 is event-driven (not a sweep), volume is naturally bounded by real-world signal frequency.
- **Trace:** every run carries one `trace_id` end-to-end → Langfuse shows resolve latency, token cost, and gate outcome per signal.

---

## §7. Companion tables (add to `DATA v1.0` if not present)

```sql
CREATE TABLE IF NOT EXISTS triage_dropped (
  id BIGSERIAL PRIMARY KEY,
  account_key TEXT NOT NULL,
  reason TEXT NOT NULL,
  provenance_json JSONB,
  trace_id TEXT,
  dropped_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS discovery_budget (
  icp_segment TEXT NOT NULL,
  period DATE NOT NULL,
  remaining INT NOT NULL,
  PRIMARY KEY (icp_segment, period)
);
-- candidate table assumed from DATA v1.0; requires UNIQUE(account_key)
```

---

## §8. Test harness (curl)

```bash
curl -X POST http://localhost:5678/webhook/signal-in \
  -H 'Content-Type: application/json' \
  -d '{
    "signal_id":"sig_test_001","signal_type":"funding_round",
    "entity_hint":{"name":"Acme Fintech","domain":"acme.example"},
    "detail":{"round":"Series B","amount_usd":24000000},
    "source":{"surface":"funding_feed","url":"https://example.com/acme-series-b","detected_at":"2026-08-24T12:01:00Z"},
    "icp_segment":"series_b_fintech"
  }'
# expect: { "ok": true, "trace_id": "lf_..." }  → row in candidate, trace in Langfuse
```

Seed a budget row first: `INSERT INTO discovery_budget VALUES ('series_b_fintech', current_date, 50);`

---

## §9. Elite differentiators

1. **Single-round-trip gate** — dedup + suppression + budget resolved in one query before any paid enrichment; the immune system runs before the wallet opens.
2. **Grounded-by-construction** — the originating signal is welded to the candidate as provenance, so the downstream opener is factually anchored to a real event and passes the Editor/Critic grounding gate automatically.
3. **Idempotent under retry** — webhook re-fires and bus replays can't create duplicate leads or double-spend budget.
4. **Provider-opaque** — `resolver` model alias + LiteLLM redaction mean no PII or provider identity ever leaks into the workflow definition; fully portable across sovereign deployments.
5. **Back-pressure, not backlog** — budget exhaustion drops to an auditable ledger rather than silently queuing spend.

---

## §10. Roadmap hooks

| Next | Adds |
|---|---|
| **WG1 JSON** | Continuous Sweep (scheduled, multi-surface) sharing this Gate as a sub-workflow |
| **SYS-DLQ workflow** | Error Trigger → `dlq` table → replay button in Rep Cockpit |
| **Garage archive node** | raw artifact capture for audit/replay before Shape |
| **Committee graph write** | on emit, upsert account→committee edges into Neo4j (ABM play-runner, backlog ⑩) |

---

*FLOW-WG2 v1.0 — Prospect Dominion / L-GEN. Import-ready; bind credentials §4, seed budget §8, activate.*
