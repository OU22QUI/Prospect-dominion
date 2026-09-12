# 💬 Prospect Dominion — W5 Conversation Loop Workflow

> **Doc code:** `FLOW-W5 v1.0` · **Type:** Executable n8n workflow (importable JSON)
> **Squad:** Conversation Squad [12] → Conversion Crew (L-CONV)
> **Consumes:** `reply.received` · inbound email (Postal) · inbound SMS · voice transcript (LiveKit/Fonoster)
> **Emits:** `reply.classified` · `reply.positive` · `lead.suppressed` · `objection.drafted` · `meeting.requested` · `conversation.facts`
> **Companion to:** `FLOW-WG2` (discovery) · `FLOW-W2` (enrichment) · `FLOW-WO1` (touch dispatch)

---

## §W5.0 — Why this workflow exists

`FLOW-WO1` sends touches and captures *outbound* outcomes. But every path in the system — email, SMS, voice — **dead-ended at the reply.** A prospect saying *"sure, let's talk"* had nowhere to go; an *"unsubscribe"* risked going unhonored; an objection cooled untended.

**W5 is the funnel's floor.** It is the single inbound consumer that:

1. **Normalizes** every inbound message (any channel) onto the shared `thread_id`.
2. **Classifies** intent and mines structured `conversation_facts` (Conversation Intelligence Svc, §5.9).
3. **Routes** deterministically: suppress opt-outs instantly · reschedule around OOO · draft grounded objection replies through the Governance gate · escalate hot intent to the Readiness Detector (WV1).
4. **Feeds the learning loop** — every reply, objection, and rebuttal becomes training data.

> **Prime directive:** never let a warm buyer cool in the gap between the AI and a human, and never let an opt-out go unhonored for even one more touch.

---

## §W5.1 — Layer stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  INGRESS      Postal inbound webhook · SMS webhook · LiveKit transcript │
│               · bus event reply.received                               │
├──────────────────────────────────────────────────────────────────────┤
│  NORMALIZE    channel adapter → canonical InboundMessage → thread bind  │
├──────────────────────────────────────────────────────────────────────┤
│  CLASSIFY     Conversation Intel Svc: intent label + conversation_facts │
│               (LiteLLM cheap/local model; Langfuse-traced)             │
├──────────────────────────────────────────────────────────────────────┤
│  ROUTE        deterministic switch on intent label                     │
├──────────────────────────────────────────────────────────────────────┤
│  ACT          suppression · cadence-reschedule · Response Drafter +     │
│               Governance gate · WV1 Readiness Detector · nurture        │
├──────────────────────────────────────────────────────────────────────┤
│  PERSIST      Postgres conversation_facts · Mem0 episodic · Garage raw  │
├──────────────────────────────────────────────────────────────────────┤
│  RESILIENCE   DLQ · idempotency · Langfuse trace · edge re-check        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## §W5.2 — Squad & tool bindings

| Role | Agent / Node | Tools |
|---|---|---|
| **Reply Classifier** | Conversation Intel Svc | LiteLLM (cheap/local), Langfuse |
| **Fact Extractor** | Conversation Intel Svc | LiteLLM, Postgres `conversation_facts`, Mem0 |
| **Suppression Handler** | Compliance node | Consent Ledger, global suppression list (all channels) |
| **Response Drafter** | Copy Squad (objection mode) | Mem0 (full thread), Qdrant+Neo4j retrieval, LiteLLM (best) |
| **Governance Gate** | Guardrails node | grounding check, unsubscribe/claim/tone gate |
| **Readiness Detector** | L-CONV WV1 | Qualifier scorecard, bus emit `reply.positive` |
| **OOO/Auto-reply Detector** | rules + classifier | cadence governor (reschedule) |

---

## §W5.3 — Intent taxonomy & routing table

| Label | Signal | Route | Human? |
|---|---|---|---|
| `interested` / `meeting_requested` | positive, readiness | → emit `reply.positive` → **WV1 Readiness Detector** → Qualifier → booking (V-1) | tier-1 optional |
| `objection` | pushback, question, price/timing | → **Response Drafter** (full history) → **Governance gate** → send / tier-1 queue | tier-1 queue |
| `referral` | "talk to X instead" | → create lead (new `thread_id`) + warm-intro graph edge; ack sender | no |
| `unsubscribe` / `opt_out` | STOP, remove me | → **Suppression** (cascade all channels) + consent ledger + **halt cadence** → emit `lead.suppressed` | no |
| `ooo` / `auto_reply` | vacation, bounce-back | → parse return date → **reschedule** cadence; no reply | no |
| `not_now` | "circle back Q3" | → move to nurture cadence at stated date | no |
| `negative` | hostile / do-not-contact | → suppress + flag; no reply | audit |
| `unknown` | low-confidence | → tier-1 human queue (never auto-send) | yes |

> **Hard rule:** `unsubscribe`, `opt_out`, and `negative` are honored **before** any other processing — suppression cannot be starved by a busy drafting branch.

---

## §W5.4 — The workflow (importable n8n JSON)

```json
{
  "name": "PD — W5 Conversation Loop",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "pd-inbound",
        "responseMode": "responseNode",
        "options": { "rawBody": true }
      },
      "id": "wh_inbound",
      "name": "Inbound Webhook (email/SMS)",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [180, 300]
    },
    {
      "parameters": {
        "rule": { "interval": [] },
        "triggerOn": "custom",
        "eventName": "reply.received"
      },
      "id": "bus_trigger",
      "name": "Bus: reply.received",
      "type": "n8n-nodes-base.nats",
      "typeVersion": 1,
      "position": [180, 480]
    },
    {
      "parameters": {
        "functionCode": "// Channel adapter → canonical InboundMessage\nconst raw = items[0].json;\nconst ch = raw.channel || (raw.From && raw.Body ? 'sms' : raw.mail_from ? 'email' : 'voice');\nlet msg = {\n  channel: ch,\n  from: raw.from || raw.From || raw.mail_from || raw.caller,\n  to: raw.to || raw.To || raw.rcpt_to,\n  body: raw.text || raw.Body || raw.plain || raw.transcript || '',\n  message_id: raw.message_id || raw.MessageSid || raw.id,\n  in_reply_to: raw.in_reply_to || raw.references || null,\n  received_at: new Date().toISOString(),\n  raw_ref: raw.raw_ref || null\n};\n// Idempotency key\nmsg.idempotency_key = 'inb:' + (msg.message_id || (msg.from + ':' + msg.received_at));\nreturn [{ json: msg }];"
      },
      "id": "normalize",
      "name": "Normalize → InboundMessage",
      "type": "n8n-nodes-base.function",
      "typeVersion": 1,
      "position": [420, 380]
    },
    {
      "parameters": {
        "operation": "get",
        "propertyName": "idempotency_key",
        "key": "={{$json[\"idempotency_key\"]}}"
      },
      "id": "idem_check",
      "name": "Idempotency Guard (Redis)",
      "type": "n8n-nodes-base.redis",
      "typeVersion": 1,
      "position": [640, 380]
    },
    {
      "parameters": {
        "conditions": { "string": [ { "value1": "={{$json[\"seen\"]}}", "operation": "isEmpty" } ] }
      },
      "id": "if_new",
      "name": "IF new message",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [860, 380]
    },
    {
      "parameters": {
        "url": "http://conversation-intel:8080/thread/bind",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"from\":$json[\"from\"],\"in_reply_to\":$json[\"in_reply_to\"],\"channel\":$json[\"channel\"]}"
      },
      "id": "thread_bind",
      "name": "Bind thread_id",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1080, 300]
    },
    {
      "parameters": {
        "url": "http://conversation-intel:8080/classify",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"thread_id\":$json[\"thread_id\"],\"body\":$json[\"body\"],\"channel\":$json[\"channel\"]}",
        "options": { "timeout": 20000 }
      },
      "id": "classify",
      "name": "Classify + Extract Facts",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1300, 300]
    },
    {
      "parameters": {
        "url": "http://postgres-svc:8080/conversation_facts",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"thread_id\":$json[\"thread_id\"],\"facts\":$json[\"facts\"],\"label\":$json[\"label\"],\"sentiment\":$json[\"sentiment\"]}"
      },
      "id": "persist_facts",
      "name": "Persist conversation_facts",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1520, 300]
    },
    {
      "parameters": {
        "dataType": "string",
        "value1": "={{$json[\"label\"]}}",
        "rules": {
          "rules": [
            { "value2": "unsubscribe", "output": 0 },
            { "value2": "opt_out", "output": 0 },
            { "value2": "negative", "output": 0 },
            { "value2": "ooo", "output": 1 },
            { "value2": "auto_reply", "output": 1 },
            { "value2": "objection", "output": 2 },
            { "value2": "interested", "output": 3 },
            { "value2": "meeting_requested", "output": 3 },
            { "value2": "referral", "output": 4 },
            { "value2": "not_now", "output": 5 }
          ]
        },
        "fallbackOutput": 6
      },
      "id": "route",
      "name": "Route on intent",
      "type": "n8n-nodes-base.switch",
      "typeVersion": 3,
      "position": [1740, 300]
    },
    {
      "parameters": {
        "url": "http://compliance-svc:8080/suppress",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"thread_id\":$json[\"thread_id\"],\"contact\":$json[\"from\"],\"scope\":\"all_channels\",\"reason\":$json[\"label\"],\"halt_cadence\":true}"
      },
      "id": "suppress",
      "name": "Suppress + Halt Cadence",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1980, 120]
    },
    {
      "parameters": {
        "url": "http://cadence-svc:8080/reschedule",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"thread_id\":$json[\"thread_id\"],\"resume_at\":$json[\"facts\"][\"return_date\"],\"reason\":\"ooo\"}"
      },
      "id": "reschedule",
      "name": "Reschedule around OOO",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1980, 240]
    },
    {
      "parameters": {
        "url": "http://copy-svc:8080/draft/objection",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"thread_id\":$json[\"thread_id\"],\"objection\":$json[\"facts\"][\"objection_type\"],\"history\":\"mem0\"}",
        "options": { "timeout": 30000 }
      },
      "id": "draft_objection",
      "name": "Response Drafter (grounded)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1980, 360]
    },
    {
      "parameters": {
        "url": "http://governance-svc:8080/gate",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"draft\":$json[\"draft\"],\"thread_id\":$json[\"thread_id\"],\"checks\":[\"grounding\",\"unsubscribe\",\"claims\",\"tone\"]}"
      },
      "id": "gov_gate",
      "name": "Governance Gate",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [2200, 360]
    },
    {
      "parameters": {
        "conditions": { "boolean": [ { "value1": "={{$json[\"passed\"]}}", "value2": true } ] }
      },
      "id": "if_gate",
      "name": "IF gate passed",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [2420, 360]
    },
    {
      "parameters": {
        "rule": { "interval": [] },
        "triggerOn": "custom",
        "eventName": "reply.positive"
      },
      "id": "emit_positive",
      "name": "Emit reply.positive → WV1",
      "type": "n8n-nodes-base.nats",
      "typeVersion": 1,
      "position": [1980, 480]
    },
    {
      "parameters": {
        "url": "http://leadgen-svc:8080/lead/from_referral",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"referred_by\":$json[\"thread_id\"],\"referral\":$json[\"facts\"][\"referral_target\"]}"
      },
      "id": "referral_lead",
      "name": "Create referral lead + graph edge",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1980, 600]
    },
    {
      "parameters": {
        "url": "http://cadence-svc:8080/nurture",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"thread_id\":$json[\"thread_id\"],\"resume_at\":$json[\"facts\"][\"revisit_date\"]}"
      },
      "id": "nurture",
      "name": "Move to nurture",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1980, 720]
    },
    {
      "parameters": {
        "url": "http://cockpit-svc:8080/queue/tier1",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"thread_id\":$json[\"thread_id\"],\"reason\":\"unknown_intent_or_gate_fail\",\"payload\":$json}"
      },
      "id": "human_queue",
      "name": "Human Tier-1 Queue (Cockpit)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [2640, 480]
    },
    {
      "parameters": {
        "functionCode": "// DLQ: capture any failed branch\nreturn [{ json: { dlq: true, error: $json.error || 'unknown', payload: $json, ts: new Date().toISOString() } }];"
      },
      "id": "dlq",
      "name": "Dead-Letter Queue",
      "type": "n8n-nodes-base.function",
      "typeVersion": 1,
      "position": [2640, 720]
    },
    {
      "parameters": { "respondWith": "text", "responseBody": "ok" },
      "id": "ack",
      "name": "200 ACK",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [640, 200]
    }
  ],
  "connections": {
    "Inbound Webhook (email/SMS)": { "main": [[{ "node": "200 ACK", "type": "main", "index": 0 }, { "node": "Normalize → InboundMessage", "type": "main", "index": 0 }]] },
    "Bus: reply.received": { "main": [[{ "node": "Normalize → InboundMessage", "type": "main", "index": 0 }]] },
    "Normalize → InboundMessage": { "main": [[{ "node": "Idempotency Guard (Redis)", "type": "main", "index": 0 }]] },
    "Idempotency Guard (Redis)": { "main": [[{ "node": "IF new message", "type": "main", "index": 0 }]] },
    "IF new message": { "main": [[{ "node": "Bind thread_id", "type": "main", "index": 0 }], []] },
    "Bind thread_id": { "main": [[{ "node": "Classify + Extract Facts", "type": "main", "index": 0 }]] },
    "Classify + Extract Facts": { "main": [[{ "node": "Persist conversation_facts", "type": "main", "index": 0 }]] },
    "Persist conversation_facts": { "main": [[{ "node": "Route on intent", "type": "main", "index": 0 }]] },
    "Route on intent": { "main": [
      [{ "node": "Suppress + Halt Cadence", "type": "main", "index": 0 }],
      [{ "node": "Reschedule around OOO", "type": "main", "index": 0 }],
      [{ "node": "Response Drafter (grounded)", "type": "main", "index": 0 }],
      [{ "node": "Emit reply.positive → WV1", "type": "main", "index": 0 }],
      [{ "node": "Create referral lead + graph edge", "type": "main", "index": 0 }],
      [{ "node": "Move to nurture", "type": "main", "index": 0 }],
      [{ "node": "Human Tier-1 Queue (Cockpit)", "type": "main", "index": 0 }]
    ] },
    "Response Drafter (grounded)": { "main": [[{ "node": "Governance Gate", "type": "main", "index": 0 }]] },
    "Governance Gate": { "main": [[{ "node": "IF gate passed", "type": "main", "index": 0 }]] },
    "IF gate passed": { "main": [[], [{ "node": "Human Tier-1 Queue (Cockpit)", "type": "main", "index": 0 }]] }
  },
  "settings": { "executionOrder": "v1", "saveExecutionProgress": true, "errorWorkflow": "PD — Global DLQ" },
  "tags": [{ "name": "prospect-dominion" }, { "name": "conversation" }, { "name": "W5" }]
}
```

---

## §W5.5 — Import & configuration notes

1. **Two triggers, one core.** The HTTP webhook (`/pd-inbound`) serves Postal inbound-email routes and the SMS provider; the NATS trigger serves `reply.received` from voice transcripts. Both fan into the same normalizer.
2. **ACK immediately, process async.** The webhook returns `200` before classification runs so Postal/SMS never retry-storm. All heavy work is downstream of the ACK.
3. **Idempotency is mandatory.** `idempotency_key` is checked in Redis (SETNX with 72h TTL); duplicate deliveries (common with email) are dropped silently.
4. **Suppression is starvation-proof.** The `unsubscribe/opt_out/negative` branch calls `compliance-svc` with `halt_cadence:true` — it cancels all queued touches on the `thread_id` and cascades the suppression across every channel via the consent ledger.
5. **Nothing auto-sends without the gate.** Objection drafts must pass `governance-svc` (grounding + unsubscribe presence + claim check + tone). Gate failures and `unknown` intents route to the Cockpit Tier-1 queue — never auto-sent.
6. **Model routing.** Classification/extraction use the cheap/local model; objection drafting uses the best model (§5.10 economics). Every LLM call is Langfuse-traced with the `thread_id`.
7. **Service endpoints** are placeholders (`conversation-intel`, `compliance-svc`, `copy-svc`, `governance-svc`, `cadence-svc`, `cockpit-svc`, `leadgen-svc`) — wire to the docker-compose service names in `INFRA v1.0`.

---

## §W5.6 — Persistence contract

| Store | Written | Purpose |
|---|---|---|
| **Postgres** | `conversation_facts` (label, objection_type, use_case, competitor, budget/timing cue, next_step, sentiment) | queryable/auditable truth |
| **Mem0** | episodic thread memory | Response Drafter context; carried into human handoff |
| **Garage** | raw inbound (email MIME / transcript) | evidence, coaching, compliance |
| **Neo4j** | referral edge (`contact -REFERRED-> contact`) | warm-intro graph |
| **Consent Ledger** | suppression event + basis | GDPR/CCPA/CAN-SPAM erasure cascade |

---

## §W5.7 — SLOs & compliance

- **SLOs:** inbound → classified < 10 s · opt-out → suppression effective < 5 s (before any next touch) · objection draft → gate < 30 s · positive intent → `reply.positive` emitted < 5 s.
- **Compliance:** every suppression writes the consent ledger with a basis and cascades erasure; objection/reply drafts inherit the consent basis from L-OMNI; raw transcripts in Garage are access-controlled and erasure-cascaded.
- **Fail-safe:** on any downstream error the DLQ captures the full payload; the message is **never** silently lost, and suppression-class messages are retried with priority.

---

## §W5.8 — Roadmap

| Version | Addition |
|---|---|
| v1.1 | Multi-language classification; per-segment objection-rebuttal library auto-fed from closed-won |
| v1.2 | Mid-thread sentiment-drift detection → proactive human escalation |
| v1.3 | Cross-thread use-case mining (team-level) feeding the value-prop library (§5.9) |
| v1.4 | Voice barge-in live-classification path (LiveKit real-time) sharing the same taxonomy |

---

## §W5.9 — Elite differentiators

- **One taxonomy, every channel.** Email, SMS, and voice replies classify through the *same* intent model onto the *same* `thread_id` — no per-channel logic drift.
- **Suppression cannot be starved.** Opt-outs are honored on a dedicated priority path before any drafting, closing the single biggest compliance risk in cold outreach.
- **Grounded objection handling.** Rebuttals cite real thread history and account facts through the Governance gate — no hallucinated promises reach a prospect.
- **The reply is training data.** Every objection + winning rebuttal becomes a reusable copy asset and a signal to the learning loop — the system gets better at the exact objections your market raises.
- **Baton pass at full speed.** Positive intent emits `reply.positive` to WV1 in < 5 s — the human joins a conversation already in motion, not a cold CRM record.

---

*FLOW-W5 v1.0 — the funnel's floor. Every reply captured, every opt-out honored, every warm buyer handed off at full speed.*
