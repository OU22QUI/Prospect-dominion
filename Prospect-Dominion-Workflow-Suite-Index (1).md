# 🗺️ Prospect Dominion — Workflow Suite Index & Orchestration Map

> **Doc code:** `FLOW-INDEX v1.0` · **Type:** Orchestration map (binds all executable workflows into one deployable system)
> **Squad:** All crews — this is the connective tissue
> **Consumes / Emits:** the complete event chain (see §I.3)
> **Companion to:** every `FLOW-*` doc · `INFRA v1.0` · `DATA v1.0` · L-OMNI (orchestration brain) · L-LEARN (flywheel)

---

## §I.0 — Why this doc exists

Seven executable workflow docs now exist. Imported raw, they are seven islands. **This doc is the bridge.** It defines the single event chain they share, the one contract that spans them (`thread_id`), and the exact order to enable them so the system boots safe and learns from day one.

If you read one doc before deploying, read this one.

---

## §I.1 — The suite at a glance

| # | Doc code | Workflow | Consumes | Emits | Cadence |
|---|---|---|---|---|---|
| 1 | `FLOW-WG2` | Signal-First Discovery | signals (webhook/RSS/schedule) | `lead.discovered` | event + poll |
| 2 | `FLOW-W2` | Enrichment & Email Hunt | `lead.discovered` | `lead.enriched` · `lead.scored` | queue-driven |
| 3 | `FLOW-WO1` | Touch Dispatcher | `touch.planned` | `touch.sent` · `touch.failed` | queue-driven |
| 4 | `FLOW-W5` | Conversation Loop | inbound message (Postal/webhook) | `reply.classified` · `reply.positive` · `lead.suppressed` | event |
| 5 | `FLOW-WV` | Readiness & Booking | `reply.positive` | `meeting.booked` · `lead.dq` | event |
| 6 | `FLOW-WL1` | Outcome Ingest | **all** outcome events | `outcome.logged` | always-on sub |
| 7 | `FLOW-WL2-6` | Learning Flywheel | `outcome.logged` + `outcome_log` | `model.promoted` · `icp.diff_proposed` · `drift.alert` | scheduled + gated |

> **Not a FLOW doc, but in the chain:** the **Orchestration Brain** (L-OMNI) sits between `lead.scored` and `touch.planned` — it owns cadence, eligibility (O-0), and the shared `thread_id`. WO1 is its dispatch arm. See §I.4.

---

## §I.2 — The one contract: `thread_id`

Every prospect gets **one `thread_id` at discovery**, and it is carried unchanged through every workflow above. It is the join key across L-OMNI (touches), L-CONV (replies, bookings), L-LEARN (outcomes), and L-SEND (sends).

- **Minted by:** `FLOW-WG2` at Triage Gate pass, alongside the canonical entity resolution (account · committee · person).
- **Carried by:** every event payload, every Postgres row, every Neo4j edge, every Langfuse trace, every Garage artifact pointer.
- **Never reassigned.** Merges (entity resolution in W2) fold one `thread_id` into another with an alias record — never a silent overwrite.

> If a workflow can't bind its work to a `thread_id`, it DLQs. No orphan events.

---

## §I.3 — The complete event chain

```
 signal ─▶ FLOW-WG2 ─ lead.discovered ─▶ FLOW-W2 ─ lead.scored ─▶
                                                          │
                                            [Orchestration Brain · O-0 gate]
                                                          │ touch.planned
                                                          ▼
                                                     FLOW-WO1 ─ touch.sent ─▶ (prospect)
                                                          │
                                          inbound reply ──┘
                                                          ▼
                                    FLOW-W5 ─ reply.classified ──┬─ reply.positive ─▶ FLOW-WV ─ meeting.booked
                                                                 ├─ objection ─▶ (back to Brain, reframe)
                                                                 └─ unsubscribe ─▶ lead.suppressed (hard stop)
                                                          
   ═══════════ every box above also emits outcome events ═══════════
                                                          ▼
                                     FLOW-WL1 ─ outcome.logged ─▶ FLOW-WL2-6 (attribute→retrain→prove→promote→watch)
                                                          │
                                          model.promoted / icp.diff  (version bump, no redeploy)
                                                          ▼
                              writeback ─▶ WG2 targeting · W2 scoring · WO1 copy/channel · Brain cadence
```

**The loop closes:** what WL2-6 learns from outcomes changes how WG2 discovers and WO1 writes — via version bump, not redeploy.

---

## §I.4 — Events: full producer/consumer matrix

| Event | Produced by | Consumed by | Notes |
|---|---|---|---|
| `lead.discovered` | WG2 | W2, WL1 | carries `thread_id`, source surface, ICP-fit@discovery |
| `lead.enriched` | W2 | Brain, WL1 | 10-layer OSINT complete |
| `lead.scored` | W2 | Brain, WL1 | predictive intent + ICP-fit |
| `touch.planned` | Brain (L-OMNI) | WO1 | cadence step; carries channel + variant |
| `touch.sent` / `touch.failed` | WO1 | Brain, WL1 | outcome + deliverability signal |
| `reply.classified` | W5 | Brain, WL1 | intent label + sentiment |
| `reply.positive` | W5 | WV | triggers readiness scorecard |
| `lead.suppressed` | W5, WV | Brain (hard stop), WL1 | opt-out / DNC — irreversible |
| `meeting.booked` / `meeting.held` / `meeting.no_show` | WV | CRM, WL1 | the money events |
| `lead.dq` | WV | Brain, WL1 | scorecard fail |
| `deal.won` / `deal.lost` | CRM/Cockpit | WL1 | ground-truth labels |
| `email.bounced` | L-SEND | WO1, WL1 | reputation + list hygiene |
| `outcome.logged` | WL1 | WL2, WL6 | fan-out for learning |
| `model.promoted` / `icp.diff_proposed` | WL5 | WG2, W2, WO1, Brain | version bump writeback |
| `drift.alert` | WL6 | Cockpit, WL3 | can trigger early retrain |

---

## §I.5 — Enable order (the boot sequence)

Turn workflows on in this order. The rules come from each layer's build-order §; violating them creates either reputation damage or perishable-label loss.

1. **`FLOW-WL1` — first and immediately.** Labels are perishable and cumulative. Even before you send anything, harvest every outcome. *(L-LEARN §L.6)*
2. **`INFRA` + `DATA`** live — Postgres/Neo4j/Qdrant + event bus up; Wave-2 exit gate. *(INFRA v1.0)*
3. **Domain Factory + Warmup Mesh** (L-SEND) — stand up sending domains and **let reputation age before any cold send.** *(L-SEND)*
4. **`FLOW-WG2`** — turn on harvesting/discovery; `thread_id` minting begins. *(L-GEN)*
5. **`FLOW-W2`** — enrichment consumes discoveries.
6. **Orchestration Brain + O-0 eligibility/consent gate** — no channel goes live until O-0 is enforced. *(L-OMNI)*
7. **`FLOW-WO1`** — dispatch, only after warmup mesh reputation is aged and O-0 is live.
8. **`FLOW-W5`** — inbound reply handling (needs Postal inbound + `thread_id` binding).
9. **`FLOW-WV`** — V-0 scorecard **before** V-1 booking (never book unqualified). *(L-CONV)*
10. **`FLOW-WL2-6`** — attribution first (needs ≥1 window), then retrain/eval/promote/watch.

> **The two hard gates, restated:** (a) reputation must age before cold send; (b) O-0 consent/eligibility before any channel — and V-0 before V-1.

---

## §I.6 — Shared resilience contract

Every FLOW doc implements the same spine, so the suite behaves uniformly:

- **Idempotency** — every event keyed; replays are safe.
- **DLQ** — anything that can't bind a `thread_id` or fails N retries lands in a dead-letter queue with reason, never silently dropped.
- **At-least-once → exactly-once** at the persistence boundary (dedup on append).
- **Langfuse trace** on every node — one trace per `thread_id` spans all seven workflows.
- **Consent snapshot** captured at each outcome (basis-at-time), so erasure and audit are exact.
- **Politeness / rate budgets** at every egress (crawl in WG2/W2, send in WO1).

---

## §I.7 — What "done" looks like

When all seven are enabled and green:

- A signal hits WG2 and, within the cadence, becomes a `thread_id` with a scored, enriched profile.
- The Brain plans touches; WO1 sends them through aged, reputation-safe domains under O-0.
- Replies flow into W5, get classified, and positive intent routes to WV's scorecard → booked meeting.
- Every step drops an outcome into WL1; the nightly/weekly flywheel attributes, retrains, proves in shadow, and (with a human on the high-impact switch) promotes improvements back into discovery, scoring, and copy — **no redeploy.**

That is Prospect Dominion running as one organism: **find → enrich → reach → converse → qualify → book → hand off → learn.**

---

## §I.8 — Roadmap: what still bolts onto this spine

The suite is the operational core. The backlog elite-edge layers (⑦–⑬) all attach to the event chain above without changing it:

| Layer | Attaches at | Adds |
|---|---|---|
| ⑦ Governance & Trust Control Plane | every LLM egress (W5 drafts, WV briefs) | fact-grounding, brand-safety gate, kill switch |
| ⑧ Rep Cockpit | WV handoff + WL5 approvals | human approve/override/coach surface |
| ⑨ MLOps / Model Sovereignty | WL3/WL4/WL5 | local fine-tune, registry, eval, drift |
| ⑩ ABM / Buying-Committee | Brain + Neo4j | champion/blocker/economic-buyer play-runner |
| ⑪ Competitive & Market Intel | WG2/W2 enrichment | competitor moves, auto-battlecards |
| ⑫ Personalized Content & Microsite | WO1 touches | per-prospect landing pages, personalized video |
| ⑬ Warm-Intro / Relationship Graph | Brain routing | mine team network for warm paths |

**Next build:** start ⑦ (Governance) — it wraps the LLM egress points the live pipeline already has, so it protects real traffic the moment sends go live.
