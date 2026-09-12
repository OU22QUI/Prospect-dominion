# 📅 Prospect Dominion — WV Readiness & Booking Workflow

> **Doc code:** `FLOW-WV v1.0` · **Type:** Executable n8n workflow (importable JSON)
> **Squad:** Conversion Crew (L-CONV) — Qualifier · Scheduler · Packager
> **Consumes:** `reply.positive` · `call.interested` · `meeting.requested` (from `FLOW-W5` / L-OMNI voice)
> **Emits:** `lead.sql` · `lead.dq` · `meeting.booked` · `meeting.confirmed` · `handoff.requested` · `nurture.return`
> **Companion to:** `FLOW-W5` (conversation loop) · `FLOW-WO1` (touch dispatch) · L-CONV §V.3–V.8

---

## §WV.0 — Why this workflow exists

`FLOW-W5` detects the moment a prospect turns warm and emits `reply.positive`. But interest is not pipeline. Between *"sure, let's talk"* and a human closer sitting in a booked call, four things must happen without a beat of delay: **qualify, book, package, route.** Miss any one and the warmest lead in the system cools in a queue.

**WV is the baton pass at full speed.** It is the single consumer of readiness events that:

1. **Qualifies** by merging all prior signal into an accretive BANT/MEDDIC scorecard, then makes an **explainable SQL call** (V-0).
2. **Books** at peak intent — offers timezone-correct live slots on any channel, books, and sends dual confirmations (V-1).
3. **Assembles** the one-document handoff packet and attaches it to the AE invite.
4. **Routes** the ready meeting to an owner by territory/capacity, or returns unqualified leads to nurture with the gap noted.

> **Prime directive:** never let a warm, ready buyer cool off in the gap between the AI and a human. Qualify first, then book — booking unqualified leads only wastes a human's time.

---

## §WV.1 — Layer stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  INGRESS      bus events reply.positive · call.interested ·            │
│               meeting.requested  → thread bind (shared thread_id)       │
├──────────────────────────────────────────────────────────────────────┤
│  QUALIFY      Qualifier: merge signal → BANT/MEDDIC scorecard →         │
│               explainable SQL score (V-0 gate)                         │
├──────────────────────────────────────────────────────────────────────┤
│  GATE         SQL threshold? → book · else → nurture.return (gap noted) │
├──────────────────────────────────────────────────────────────────────┤
│  BOOK         Meeting Orchestrator: live availability → slot offer →    │
│               book → dual confirm → invite (V-1)                        │
├──────────────────────────────────────────────────────────────────────┤
│  PACKAGE      Handoff Packager: assemble brief → Garage → attach invite │
├──────────────────────────────────────────────────────────────────────┤
│  ROUTE        territory/capacity/vertical/language → assign owner       │
├──────────────────────────────────────────────────────────────────────┤
│  PERSIST      Postgres qualification·meeting·handoff · Mem0 · Garage    │
├──────────────────────────────────────────────────────────────────────┤
│  RESILIENCE   DLQ · idempotency · calendar-lock · Langfuse trace        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## §WV.2 — Squad & tool bindings

| Role | Agent / Node | Tools |
|---|---|---|
| **Qualifier** | Conversion Crew | Conversation Intel facts, Neo4j (committee), Postgres `qualification`, LiteLLM (cheap extract) |
| **SQL Scorer** | Qualifier (explain mode) | LiteLLM, scorecard rubric, Langfuse |
| **Scheduler** | Meeting Orchestrator | CalDAV/calendar API, timezone resolver, L-OMNI channels (email/SMS reply) |
| **Packager** | Conversion Crew | Postgres, Mem0, Qdrant, Neo4j, Garage (render + store) |
| **Router** | Assignment node | territory/capacity rules table, round-robin state |
| **Governance Gate** | Guardrails node | packet PII/access check, claim/tone gate on any prospect-facing copy |

---

## §WV.3 — WV1 · Readiness Detector (V-0 scorecard)

**Trigger:** bus `reply.positive` | `call.interested` | `meeting.requested`.

1. **Bind** to the existing `thread_id`; load full conversation + enrichment context (Mem0 episodic, Postgres truth, Neo4j committee).
2. **Accretive merge** — pull every prior signal into the living scorecard. *No prospect is asked anything the system already knows.*
   - **BANT:** Budget signal, Authority (role + committee position from Neo4j), Need (pain from conversation_facts + OSINT), Timing (stated or inferred).
   - **MEDDIC option** for enterprise plays: Metrics, Economic buyer, Decision criteria/process, Identify pain, Champion.
3. **SQL score (0–100)** via LiteLLM against a fixed rubric — **always with explanation**: the top 3 reasons it crossed (or missed) the line. Sales must trust it.
4. **Gate:**
   - `score ≥ SQL_THRESHOLD` → emit `lead.sql` → proceed to **WV2 Booking**.
   - `score < threshold` → emit `nurture.return` with the **specific gap** (e.g. "no budget signal") so the Orchestration Brain nurtures precisely, not generically.
   - `disqualify` (bad fit / competitor / no-fit vertical) → emit `lead.dq` with reason; suppress from active cadence.

> **Threshold, not a form.** Qualification accretes continuously across every touch. The SQL decision is a threshold crossing — this is what lets the system book at peak intent instead of after a discovery call.

---

## §WV.4 — WV2 · Booking Flow (V-1)

**Trigger:** `lead.sql`.

1. **Resolve timezone** from enrichment (company HQ / stated) → correct for the prospect, never the AE.
2. **Read live availability** across eligible AE calendars (CalDAV/calendar API); cache availability to respect rate limits (§WV.8).
3. **Offer real slots** on the channel the interest arrived on:
   - **Email/SMS:** 3 timezone-correct slots + a booking link fallback.
   - **Voice (mid-call, via L-OMNI):** "Thursday at 2 works" → booked live before hang-up. Tightest interest-to-commitment loop possible.
4. **Book with a calendar lock** (§WV.6) to guarantee zero double-booking under concurrency.
5. **Dual confirmation** — calendar invite + confirmation message to **both** sides; the handoff packet (§WV.5) attaches to the AE's invite.
6. **Emit `meeting.booked`** → triggers **WV-Package** (handoff assembly) and **WV-Route** (owner assignment) in parallel; on confirmation receipt emit `meeting.confirmed`.

*No-show handling (reminder ladder, reschedule, missed-meeting re-engagement) is owned by a separate workflow, `FLOW-WV3`, so the booking core stays lean.*

---

## §WV.5 — The Handoff Packet (assembled here, delivered to the Cockpit)

Assembled by the Packager the instant `meeting.booked` fires; rendered to Garage and attached to the AE invite. Contains:

1. **One-line why-now** — the trigger event that made them warm.
2. **Company + person snapshot** — from OSINT enrichment (W2).
3. **Qualification scorecard** — BANT/MEDDIC filled, SQL score **+ explanation**, remaining gaps.
4. **Full conversation thread** — every touch, every reply, in order (same `thread_id`).
5. **Buying committee map** — champion / economic buyer / blocker (Neo4j).
6. **Psychographic brief** — decision style, communication preference, risk tolerance → *how to talk to them.*
7. **Suggested opening + likely objections** with pre-drafted rebuttals.

> **The packet is the product.** The human opens one document and knows everything — no re-discovery, no "tell me about your company again." SLO: packet ready < 60 s after booking; **zero handoffs without a complete packet.**

---

## §WV.6 — Concurrency, idempotency & the calendar lock

- **Idempotency key** = `thread_id + readiness_event_id`. Re-delivered readiness events never double-qualify or double-book.
- **Calendar lock:** booking acquires a short-lived advisory lock (Postgres `pg_advisory_xact_lock` keyed on `ae_id + slot`) around the read-availability → write-booking critical section. Two concurrent hot leads can never claim the same slot.
- **Booking is exactly-once:** the `meeting` row upserts on `(thread_id)`; a retry after a partial failure reconciles rather than duplicates.
- **Compensating action:** if invite-send fails after the slot is written, the slot is released and the event re-queued — never a ghost booking.

---

## §WV.7 — Node graph (importable JSON shape)

```
[Bus Trigger: reply.positive/call.interested/meeting.requested]
        │
        ▼
[Fn: bind thread_id + idempotency guard] ──dup──▶ [NoOp: ack]
        │
        ▼
[Merge: load Mem0 + Postgres + Neo4j context]
        │
        ▼
[Qualifier (LiteLLM cheap): accretive BANT/MEDDIC + SQL score+explain]
        │
        ▼
[Switch: SQL gate]
  ├─ dq ─────────▶ [Emit lead.dq + suppress] ─▶ [Persist]
  ├─ below ──────▶ [Emit nurture.return {gap}] ─▶ [Persist]
  └─ sql ────────▶ [Emit lead.sql]
                        │
                        ▼
                 [Timezone resolve] ─▶ [Read availability (cached)]
                        │
                        ▼
                 [Offer slots on origin channel]  ◀── (voice: mid-call book via L-OMNI)
                        │
                        ▼
                 [Acquire calendar lock] ─▶ [Book slot] ─▶ [Release lock]
                        │
                        ▼
                 [Dual confirm: invite + prospect msg] ─▶ [Emit meeting.booked]
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
[WV-Package: Handoff Packager]   [WV-Route: assign owner]
        │                               │
        ▼                               ▼
[Garage render + attach invite]  [territory/capacity/round-robin]
        │                               │
        └───────────────┬───────────────┘
                        ▼
                 [Emit handoff.requested → Rep Cockpit]
                        │
                        ▼
                 [Persist: Postgres qualification·meeting·handoff · Mem0 · Garage]

  (any node error) ─▶ [DLQ + Langfuse trace + alert]
```

---

## §WV.8 — Scaling, cost, observability, compliance

- **Scaling:** qualification + packaging are cheap (retrieval + one LLM synthesis) — scale horizontally off the event queue. **The real constraint is the calendar API rate limit**; cache availability windows and refresh on a short TTL rather than per-request.
- **Cost:** tiered models — cheap/local model for scorecard extraction, premium model only for final packet synthesis on high-value accounts.
- **Observability (Langfuse):** SQL→booked rate · booked→held (show) rate · held→AE-accepted rate · AE-reject reasons · **time-from-interest-to-booked** (the decay metric) · packet-completeness score.
- **SLOs:** interest → slot offered < 2 min · booked → packet ready < 60 s · zero handoffs without a complete packet.
- **Compliance:** qualification notes and recordings **inherit the consent basis** from L-OMNI; handoff packets contain PII → access-controlled in the Cockpit; erasure cascades from the consent ledger; AE-visible data respects data-minimization.

---

## §WV.9 — Failure modes & guards

| Failure | Guard |
|---|---|
| Double-book under concurrent hot leads | Postgres advisory lock around read-avail → write-book |
| Duplicate readiness event | Idempotency key `thread_id + event_id` |
| Invite send fails after slot written | Compensating release + re-queue (no ghost booking) |
| Calendar API rate-limited | Cached availability + backoff; DLQ on exhaustion |
| SQL score with no explanation | Hard-fail the node — explainability is non-negotiable |
| Packet incomplete at booking | Block `handoff.requested`; retry Packager; alert |
| Timezone ambiguity | Default to prospect-stated; else company HQ; never AE-local |

---

## §WV.10 — Import & configuration notes

- **Import:** n8n → Import from File → set credentials for CalDAV/calendar API, Postgres, Neo4j, Mem0, Garage (S3), LiteLLM, Langfuse.
- **Env:** `SQL_THRESHOLD` (default 70), `AVAILABILITY_TTL_S` (default 120), `SLOT_OFFER_COUNT` (default 3), `LLM_QUALIFY_MODEL`, `LLM_PACKET_MODEL`.
- **Round-robin state:** stored in Postgres `assignment_state`; survives restarts.
- **Build-order rule:** ship **WV1 (V-0 scorecard) before WV2 (V-1 booking).** Qualify first, then book.
- **Companion workflows:** `FLOW-WV3` (no-show & reschedule ladder), `FLOW-WV-Outcome` (AE accept/reject + deal stage → Self-Improvement / ICP updater / Source Genome).

---

## §WV.11 — Elite differentiators

- **Baton pass at full speed.** Most stacks drop warm leads into a CRM queue and pray. Dominion books at peak intent and hands a human a conversation already in motion.
- **Explainable SQL.** Every score ships with its reasons — the only way an AE trusts an AI-qualified meeting.
- **Mid-call booking.** Via L-OMNI, the voice agent books *during the call* — the tightest interest-to-commitment loop possible.
- **The packet no rep has to build.** A living brief pulled from five memory stores in 60 seconds — the thing SDRs spend hours on.

---

*Module `FLOW-WV v1.0` — the funnel's floor, made executable. With WG2 → W2 → WO1 → W5 → **WV**, the pipeline is end-to-end: **find → enrich → reach → converse → qualify → book → hand off.** Next executable link: `FLOW-WV3` (no-show engine) and `FLOW-WV-Outcome` (the feedback tap into L-LEARN).*
