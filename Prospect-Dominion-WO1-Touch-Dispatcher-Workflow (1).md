# 📮 Prospect Dominion — WO1 Touch Dispatcher Workflow

### Executable n8n Workflow — Module **FLOW-WO1 v1.0**

> **House style:** layer stack · squads · §-numbering · event-driven · workflows · roadmap · elite differentiators.
> **Companion to:** `FLOW-WG2 v1.0` (Signal-First Discovery) · `FLOW-W2 v1.0` (Enrichment & Email Hunt) · `L-OMNI v1.0` (§O.8 WO1) · `L-SEND v1.0` (sending substrate) · `DATA v1.0` (schemas) · `INFRA v1.0` (services/ports).

---

## §D.0 — Where This Workflow Sits

WO1 is the **edge of the send**. Everything upstream decides *whether* and *what* to send; WO1 is the last gate before a real transport carries a real message to a real human. It is the executable form of **L-OMNI §O.8 WO1 — Touch Dispatcher**.

```
        [ Orchestration Brain — Next-Best-Action ]   (L-OMNI §O.5)
                          │  emits: touch.planned {thread_id, prospect, channel, intent, payload}
                          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    WO1 — TOUCH DISPATCHER                     │
   │  ingest → resolve thread → EDGE ELIGIBILITY (O-0 last check) │
   │  → render → channel router → deliver → capture outcome        │
   └─────────────────────────────────────────────────────────────┘
        │ email          │ voice        │ sms         │ linkedin
        ▼                ▼              ▼             ▼
   [ L-SEND ]      [ Fonoster +   [ Fonoster/    [ Headless
   Rotation +        LiveKit ]      SIP-SMS ]      browser,
   Cadence Gov.                                    rate-gov ]
        │                │              │             │
        └──────── outcome → touch{} + conversation{thread_id} (Postgres) ───────┘
                          │  emits: touch.sent | touch.answered | touch.no_answer | touch.failed
                          ▼
              [ Conversation Intelligence → Brain re-plans next touch ]
```

**Prime directive:** *the Brain proposes; WO1 disposes.* The Brain's decision is advisory until WO1 confirms eligibility at the edge — because consent, DNC status, quiet hours, and budget can all change between plan and send. **A single non-eligible send is a compliance breach; a stale eligibility check is how it happens.**

---

## §D.1 — Design Principles

1. **Re-check at the edge, always.** Eligibility proven upstream is *not trusted*. WO1 re-runs the O-0 gate against live state microseconds before delivery. The gap between `touch.planned` and `deliver()` is where consent revocations hide.
2. **One thread, one truth.** WO1 never invents state. It reads and writes the shared `thread_id` (L-OMNI §O.7). The transport is stateless cattle.
3. **Fail closed.** Any ambiguity — eligibility unknown, budget unreadable, adapter timeout — results in *no send* and a re-queue, never a speculative send.
4. **Idempotent dispatch.** Every `touch.planned` carries a `touch_id`; WO1 is safe to replay. A duplicate delivery is a reputation tax and a creep-factor; the dedup key forbids it.
5. **Channel-agnostic contract.** Every adapter honors `render(payload) → deliver() → capture(outcome)`. Adding a channel never touches WO1's core.
6. **Every touch is evidence.** Delivery, non-delivery, and every provider signal are written to `touch{}` and traced in Langfuse. Nothing is fire-and-forget.

---

## §D.2 — Squads Touched

| Squad | Role in WO1 |
|---|---|
| **Omnichannel Conductor [O]** | Owns the workflow; the Conductor's `touch.planned` is the trigger. |
| **Outreach [8]** | Owns email rendering + sequence copy; consumes L-SEND for delivery. |
| **Governance & Trust [G]** | Owns the O-0 eligibility service and the suppression ledger WO1 consults. |
| **Conversation [9]** | Consumes the outcome events WO1 emits; wakes on `reply.received`. |

---

## §D.3 — Event Contract

**Consumes:** `touch.planned`
```json
{
  "touch_id": "tch_01H...",          // idempotency key — client-generated, unique per planned touch
  "thread_id": "thr_01H...",          // the one conversation id, shared across channels
  "prospect_id": "prs_01H...",
  "account_id": "acc_01H...",
  "channel": "email",                 // email | voice | sms | linkedin
  "intent": "book",                   // qualify | book | nurture | reactivate
  "payload_ref": "s3://garage/payloads/tch_01H....json",  // rendered-or-renderable content
  "planned_at": "2026-08-26T09:00:00Z",
  "brain_policy_version": "nba_v7",
  "trace_id": "lf_..."                // Langfuse trace continuity from the Brain
}
```

**Emits (one of):**
| Event | When | Downstream |
|---|---|---|
| `touch.sent` | Transport accepted the message | Conversation Intelligence; attribution |
| `touch.answered` | Live voice answered / immediate ack | Conversation squad wakes |
| `touch.no_answer` | Voice unanswered / voicemail left | Brain re-plans |
| `touch.suppressed` | Edge eligibility denied the send | Governance audit trail |
| `touch.failed` | Adapter/transport error after retries | DLQ + ops alert |

Every emitted event carries the original `touch_id`, `thread_id`, `trace_id`, and a `disposition` object.

---

## §D.4 — The Workflow, Node by Node

> Import target: n8n ≥ 1.60. All service hostnames/ports per `INFRA v1.0`. Secrets via n8n credentials, never inline.

### Stage 1 — Ingress & Idempotency
1. **Trigger — NATS Consumer** (`touch.planned`, durable queue-group `wo1-dispatch`). Manual-ack; ack only after terminal disposition.
2. **Function — Envelope Validate.** Reject malformed envelopes to DLQ immediately (schema check on required fields).
3. **Postgres — Idempotency Claim.** `INSERT ... ON CONFLICT (touch_id) DO NOTHING RETURNING id`. If no row returned → this `touch_id` is already in flight or done → **ack and stop** (safe replay).

### Stage 2 — Resolve & Freeze State
4. **Postgres — Load Thread.** Fetch `conversation{thread_id}`, prospect contactabilities, channel history, timezone.
5. **Function — Thread Affinity Pin (email only).** For email, resolve the mailbox already pinned to this `thread_id`; if none, request one from L-SEND's Rotation Orchestrator (§D.5). *No prospect ever gets two mailboxes on one thread.*

### Stage 3 — Edge Eligibility (the O-0 last check)  ⟵ *the reason WO1 exists*
6. **HTTP — Eligibility Service** (`POST /eligibility/check`, Governance squad). Payload: `{prospect_id, channel, intent, now}`. Returns a **composite verdict** over:
   - **Consent ledger** — per-channel, timestamped, source-of-consent (L-OMNI §O.7). Voice/SMS require affirmative opt-in (TCPA).
   - **DNC / suppression** — global + client-scoped suppression, unsubscribe, hard-bounce, complaint.
   - **Quiet hours** — recipient-timezone quiet window; per-channel legal windows (SMS/voice stricter).
   - **Rate budget** — per-channel daily/hourly remaining budget for this prospect *and* org ceiling.
   - **Verification freshness (email)** — address still `valid`/governed-`risky` within TTL (L-SEND §S.5); stale → re-verify or deny.
7. **Switch — Verdict.**
   - `deny` → emit `touch.suppressed` with reason code → write audit row → **ack** (this is a *success*, not an error).
   - `defer` (quiet hours / budget exhausted) → re-queue to a delay stream with computed `next_eligible_at` → ack.
   - `allow` → continue.

### Stage 4 — Render
8. **HTTP — Payload Fetch** (Garage/S3 `payload_ref`) or **Render** if only a template ref was passed.
9. **Function — Compliance Stamp.** Inject required footer/unsubscribe (email), recording-consent preamble (voice), and STOP-to-opt-out (SMS). Governance-owned templates; non-negotiable.
10. **LLM (optional, LiteLLM) — Final Personalization Hydration.** Merge live enrichment tokens; guarded by the Governance fact-grounding gate (no hallucinated claims about the prospect). Skipped if payload is pre-rendered final.

### Stage 5 — Channel Router
11. **Switch — `channel`** → one of four adapter branches. Each adapter honors `render → deliver → capture`.

**Branch C1 — Email (via L-SEND):**
- **HTTP — Cadence Governor check** (`/cadence/reserve`): reserve one send unit on the pinned mailbox; if budget just exhausted → `defer` back to Stage 3.7.
- **HTTP — Postal Send** (message assembled with mailbox identity, SPF/DKIM-signed by Postal, custom tracking domain via Garage edge).
- **Capture:** Postal message-id, accepted/deferred/rejected.

**Branch C2 — Voice (Fonoster + LiveKit):**
- **HTTP — Fonoster Originate** (SIP dial-out); attach LiveKit room; STT→LLM→TTS agent joins under the same `thread_id`.
- Two-party-consent state honored (§O.4): record only after spoken consent, else notes-only.
- **Capture:** `answered | no_answer | voicemail | busy | failed`; transcript ref.

**Branch C3 — SMS (Fonoster / SIP-SMS):**
- Session-window + STOP-handling check; send; **capture:** gateway id, delivery receipt.

**Branch C4 — LinkedIn (headless, rate-governed):**
- **HTTP — Rate-Governor reserve** (§O.10 daily action caps). If a flagged action → route to **human one-click approval** queue (ToS-safe) instead of auto-firing.
- Execute view/connect/DM at human pace; **capture:** action id, accepted/pending.

### Stage 6 — Capture & Emit
12. **Postgres — Write Touch.** Upsert `touch{touch_id, thread_id, channel, disposition, provider_ref, sent_at, ...}`; update `conversation.last_touch_*`.
13. **Function — Map Disposition → Event.** Choose `touch.sent | answered | no_answer | failed`.
14. **NATS — Emit Outcome** on the mapped subject, carrying `trace_id`.
15. **NATS — Ack** the original message (only now — after durable write + emit).

---

## §D.5 — Rotation & Cadence Integration (email)

WO1 does **not** implement rotation or throttle — it *calls* L-SEND, keeping the reputation control loop in one place.

| Concern | Owner | WO1's role |
|---|---|---|
| Mailbox selection | L-SEND Rotation Orchestrator (health-weighted, §S.6) | Request a mailbox for new threads; pin thereafter |
| Per-mailbox budget | L-SEND Cadence Governor (age × reputation ramp) | Reserve one unit; honor `defer` on exhaustion |
| Reputation exclusion | L-SEND Reputation Telemetry | Never override a mailbox exclusion — if pinned mailbox is now in rehab, request a *thread-safe reassignment* or defer |
| Tracking domain | Garage edge (§S.8) | Use the mailbox's assigned tracking CNAME |

**Rehab edge case:** if the thread-pinned mailbox entered rehab since the last touch, WO1 requests a **continuity-preserving reassignment** from the Orchestrator (same sending *identity/display name* where possible) rather than silently switching senders mid-thread — protecting the "one human wrote to me" illusion.

---

## §D.6 — Reliability & Failure Handling

| Failure | Behavior |
|---|---|
| Malformed envelope | Straight to DLQ (`wo1.dlq`); no retry; ops counter++ |
| Eligibility service down | **Fail closed** — defer with backoff; never send on unknown eligibility |
| Adapter timeout | Bounded retry (3×, exponential + jitter); then `touch.failed` → DLQ |
| Duplicate `touch_id` | Idempotency claim stops it at Stage 1.3 |
| Partial send (accepted then provider error) | Reconciliation job matches provider webhooks to `touch{}` and corrects disposition |
| Cadence budget race | `/cadence/reserve` is atomic server-side; loser gets `defer`, not double-send |

**DLQ policy:** `wo1.dlq` messages carry the full envelope + failure reason + stack. A drain workflow surfaces them to the Rep Cockpit; nothing is auto-replayed without a fix.

**Observability:** every run opens a Langfuse span under the inherited `trace_id`, tagging `channel`, `verdict`, `disposition`, mailbox id (email), and latency per stage. Voice latency is tracked against the ~800 ms budget (§O.4).

---

## §D.7 — Config & Secrets (import notes)

| Key | Source | Notes |
|---|---|---|
| `NATS_URL` | INFRA §I.x | durable consumer `wo1-dispatch` |
| `PG_DSN` | INFRA | `touch`, `conversation`, `consent_ledger`, `idempotency` |
| `ELIGIBILITY_URL` | Governance svc | `/eligibility/check` |
| `LSEND_ROTATION_URL` / `LSEND_CADENCE_URL` | L-SEND | mailbox + budget |
| `POSTAL_API` / `POSTAL_KEY` | Postal | per-org sending |
| `FONOSTER_URL` / `LIVEKIT_URL` | Voice subsystem | SIP + media |
| `GARAGE_ENDPOINT` | Garage | payloads + tracking assets |
| `LANGFUSE_*` | Langfuse | tracing |
| `LITELLM_URL` | LiteLLM | final hydration (optional) |

> **Import:** create the credentials above, set the NATS durable name, then import the workflow JSON. Run the **smoke path** (§D.8) before enabling the live trigger.

---

## §D.8 — Test & Cutover

1. **Dry-run mode** (`WO1_DRYRUN=true`): executes every stage *including eligibility* but stubs `deliver()` — verifies routing, rendering, compliance stamping, and disposition mapping with zero real sends.
2. **Eligibility red-team:** feed synthetic `touch.planned` for a DNC-listed, an unsubscribed, a quiet-hours, and a budget-exhausted prospect — assert **all four are suppressed/deferred, none delivered**.
3. **Idempotency test:** replay the same `touch_id` 3× → exactly one delivery.
4. **Channel smoke:** one real send per channel to a seed inbox/number you control.
5. **Cutover:** enable live trigger at low concurrency; watch Langfuse suppression-vs-send ratio and DLQ depth before ramping.

---

## §D.9 — Roadmap

| Phase | Addition |
|---|---|
| v1.1 | **Send-time optimization** — Brain passes a window; WO1 picks intra-window optimal slot from per-prospect open-history. |
| v1.2 | **Multi-variant at edge** — bandit-selected subject/opener variant chosen at dispatch, outcome fed to L-LEARN. |
| v1.3 | **Warm-intro interception** — if Relationship Graph finds a warm path mid-plan, WO1 can divert to a human-intro branch. |
| v2.0 | **Cross-channel atomic touch** — coordinated same-window email+LinkedIn "surround" plays with committee-level dedup. |

---

## §D.10 — Elite Differentiators

- **Eligibility at the edge, not the plan.** Most systems check consent when they *queue*; WO1 checks it when it *sends*. That closes the revocation-race window that turns a "compliant" system into a complaint magnet.
- **Fail-closed by construction.** Unknown eligibility, unreadable budget, dead adapter → *no send*. The system's default state is silence, not spray.
- **Thread-affinity through rehab.** Sender continuity survives mailbox rotation, so a prospect never notices the fleet churning underneath a conversation.
- **Suppression is a success event.** `touch.suppressed` is a first-class, audited outcome — not swallowed — feeding the compliance trail and the Brain's learning.
- **One dispatcher, four channels, zero core edits.** The `render → deliver → capture` contract means new surfaces (WhatsApp, direct mail) plug in without touching the gate.

---

*FLOW-WO1 v1.0 — the edge of the send. The Brain proposes; WO1 disposes; the fleet stays clean.*
