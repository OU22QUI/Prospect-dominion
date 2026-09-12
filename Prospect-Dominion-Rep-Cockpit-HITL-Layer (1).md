# 🎛️ Prospect Dominion — Rep Cockpit & Human-in-the-Loop Layer

> **Module ⑧ · HITL v1.0 · Elite Edge Layer**
> The operating model behind the glass. **UI-SPEC v1.0** defines the ten *screens* of the Rep Cockpit; this module defines the *decisions* those screens exist to make — what a human sees, when the machine waits for them, and how their every correction teaches the system. It resolves GOV's `cockpit-svc` bridge and WL2-6's promotion queue into a coherent human operating layer.

---

## §H.0 — Why This Module Exists

Dominion is now autonomous end to end and self-improving. Autonomy without a human operating layer is a liability; a human operator without leverage is just a call-center seat. HITL is the layer that gives one person meaningful command over thousands of concurrent touches: **surface what needs a human, hide what doesn't, and turn every human correction into training signal.**

Three upstream modules dangle into the cockpit and resolve here:
- **GOV ⑦** posts Send-Gate failures and promotion packets to `cockpit-svc`.
- **WL2-6** routes high-impact model deltas to the Rep Cockpit for one-click approve/reject.
- **W5** escalates `unknown` intents and Tier-1 accounts to the operator queue.

UI-SPEC renders these; HITL defines the routing rules, autonomy contract, and coaching loop that decide *what* is rendered and *what happens to the human's answer.*

---

## §H.1 — Layer Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  H5  COACH LOOP        Every override → labeled signal → L-LEARN        │
├──────────────────────────────────────────────────────────────────────┤
│  H4  AUTONOMY DIAL     A0 manual · A1 supervised · A2 autonomous        │
├──────────────────────────────────────────────────────────────────────┤
│  H3  DECISION QUEUES   Triage · Unibox · Tier-1 · Promotion · Alerts    │
├──────────────────────────────────────────────────────────────────────┤
│  H2  EVIDENCE FABRIC   Every score/draft/decision shows its "why"       │
├──────────────────────────────────────────────────────────────────────┤
│  H1  RBAC & IDENTITY   OIDC roles · per-surface + per-capability gates  │
└──────────────────────────────────────────────────────────────────────┘
```

The Cockpit UI (UI-SPEC) is the presentation of this stack; the stack is what makes the UI *safe and teaching* rather than merely a dashboard.

---

## §H.2 — Squads

| Squad | Owns | Surface (UI-SPEC) |
|---|---|---|
| **Attention Squad** | ranks what needs a human now; feeds the Command Center attention list | §U.6 |
| **Unibox Squad** | inbound reply triage, pre-drafts, approve/edit/send | §U.8 (operator home) |
| **Review-Queue Squad** | Triage Gate accept/reject, Tier-1 reply approval | §U.7.triage, §U.8 |
| **Promotion Squad** | renders WL2-6 explainable-delta packets; captures verdicts | §U.7 (ICP diff), §U.14 |
| **Governance Squad bridge** | Send-Gate failures + kill switch + autonomy dial | §U.14 |
| **Coach Squad** | converts overrides/edits into labeled outcomes for L-LEARN | cross-cutting |

---

## §H.3 — The Autonomy Dial (H4)

A single, per-capability control that governs how much the machine may do without a human. Set globally, overridable per capability (e.g. discovery A2, sending A1). Admin-gated (UI-SPEC §U.14.3), reachable from the top bar on every screen.

| Level | Meaning | Human role |
|---|---|---|
| **A0 · Manual** | machine proposes, does nothing until approved | approves every action |
| **A1 · Supervised** | machine acts on low-risk, queues everything else | works the queue; spot-checks auto-actions |
| **A2 · Autonomous** | machine acts; human governs exceptions + high-impact changes | handles escalations + promotion gate only |

> **Invariant:** the autonomy dial can only *lower* what GOV's gates permit — it never overrides a fail-closed gate. A2 still cannot auto-send a draft that fails the Send Gate, and still cannot auto-promote a high-impact model change. Autonomy is *speed within the seatbelt*, never removal of the seatbelt.

---

## §H.4 — What Routes to a Human (H3 · escalation contract)

The core rule: **routine automation is quiet; anything ambiguous, high-stakes, or gate-failing is loud.**

| Trigger | Source | Queue | SLA target |
|---|---|---|---|
| Send-Gate failure (grounding/claims/tone) | GOV ⑦ | **Tier-1 reply queue** | operator, same business hour |
| `unknown` / low-confidence intent | W5 | **Tier-1 reply queue** | operator, same business hour |
| Tier-1 named account reply | W5 | **Tier-1 reply queue** | owner, immediate |
| Triage candidate before enrichment spend | L-GEN G1 | **Triage queue** | batch, daily |
| High-impact model delta | WL2-6 | **Promotion queue** | manager, before next batch |
| Deliverability / drift / kill trip | GOV ⑦, W7, WL6 | **Alert center** (loud) | admin, immediate |
| Hot intent ready to book | W5 → WV1 | **Booking / live-call** | owner, immediate |

Everything **not** on this list runs autonomously (subject to the autonomy dial) and is visible for audit as "done by AI" — never demanding attention it doesn't need.

---

## §H.5 — Evidence Fabric (H2) — trust through transparency

No output the operator is asked to approve may be a black box. Every actionable item carries its *why*:

- **Scores** (intent, ICP-fit) → the factors and weights that produced them.
- **Drafts** → the retrieved signals + account facts they were grounded on (the same provenance GOV checked).
- **Classifications** → the inbound cues that drove the intent label, one-click overridable.
- **Model deltas** → the WL2 attribution evidence + WL5 shadow-eval metrics.

This is what makes approve/override a *judgment* rather than a rubber stamp — and it is the precondition for the coach loop to produce clean labels.

---

## §H.6 — The Coach Loop (H5) — the human as trainer

Every human correction is a labeled datum, not just an edit. This is HITL's highest-leverage function and its tie into the flywheel.

| Human action | Captured as | Flows to |
|---|---|---|
| Edits an AI draft before sending | draft-quality delta (before/after) | L-LEARN copy-performance (WL2) |
| Overrides an intent classification | corrected label | W5 classifier retrain (WL3/WL4) |
| Rejects a triage candidate | negative ICP signal | ICP recentroid (WL2) |
| Approves/rejects a promotion | model-verdict + reason | WL6 champion registry + audit |
| Rejects a booking as unqualified | scorecard correction | WV1 readiness calibration |

Every capture writes to the append-only `outcome_log` (WL1) with the operator identity and `thread_id`, so the machine learns *from the specific humans supervising it* — and the audit ledger records who taught what.

> **A1→A2 graduation:** as the coach loop drives auto-action agreement rates above threshold per capability, the system *recommends* raising that capability's autonomy level — earning autonomy with evidence rather than assuming it.

---

## §H.7 — RBAC & Identity (H1)

Roles come from OIDC (UI-SPEC §U.2); every surface and high-impact action declares a minimum role; the rail hides what the role can't reach.

| Role | Can | Cannot |
|---|---|---|
| **Operator (SDR/AE)** | Unibox, own prospects, review queues, live calls, approve/edit/send, book | fleet/model admin, autonomy dial, kill switch |
| **Manager** | all operator + campaigns, analytics, routing, **approve ICP changes**, coach queue | sending-fleet + governance admin |
| **Admin / RevOps** | everything incl. sending fleet, model config, connections, **governance, kill switch, autonomy dial** | — |

Every consequential action records the acting identity to the GOV audit ledger (AI vs. human, who, when, why).

---

## §H.8 — Event Contracts

**Consumes:** `gate.failed` (GOV), `model.change.proposed` (WL2-6), `reply.escalated` / `intent.unknown` (W5), `triage.candidate` (L-GEN), `deliverability.breach`, `drift.detected`.

**Emits:** `human.approved` / `human.rejected` / `human.edited`, `autonomy.changed`, `killswitch.tripped` (→ GOV), `coach.label` (→ WL1 `outcome_log`), `booking.confirmed` (→ WV).

All carry the shared `thread_id` contract (Workflow Suite Index) so a human decision is traceable to the exact prospect lifecycle and back into the flywheel.

---

## §H.9 — Service Endpoints (wire to INFRA v1.0)

| Service | Role |
|---|---|
| `cockpit-svc` | queue orchestration, verdict capture, autonomy dial, coach-label emission |
| `governance-svc` / `killswitch-svc` | Send-Gate + kill bridge (GOV ⑦) |
| `leadgen-svc`, `conversation-intel`, `copy-svc` | evidence-fabric data providers |
| Cockpit web app | the ten surfaces defined in **UI-SPEC v1.0** |

---

## §H.10 — Roadmap

- **Phase 0 — Unibox + Tier-1 queue.** Operator home live; Send-Gate failures + unknown intents land in a worked queue; approve/edit/send with evidence. *Exit: no ungoverned reply auto-sends; a human clears the queue.*
- **Phase 1 — Autonomy dial + kill.** Per-capability A0/A1/A2; kill switch on every screen; RBAC enforced. *Exit: an admin sets autonomy per capability and freezes outbound from anywhere.*
- **Phase 2 — Promotion gate.** WL2-6 explainable-delta packets rendered; one-click approve/reject with rollback. *Exit: no high-impact model change ships unapproved.*
- **Phase 3 — Coach loop.** Every override captured as a label into WL1; A1→A2 graduation recommendations. *Exit: the humans supervising the system are measurably training it.*

---

## §H.11 — Elite Differentiators

- **The human is the trainer, not the bottleneck.** Every correction is a labeled datum feeding the flywheel — supervision *compounds* into model quality instead of being pure overhead.
- **Earned autonomy.** Capabilities graduate A1→A2 on measured agreement rates, not on faith. The machine proves it deserves more rope.
- **Loud when it matters, silent when it doesn't.** One operator commands thousands of touches because the layer surfaces only ambiguity, stakes, and gate-failures — routine automation never asks for attention.
- **No black box to approve.** Every item carries its evidence, so human judgment is real judgment — which is also what makes the resulting training labels clean.
- **Autonomy inside the seatbelt.** The dial can accelerate but never disables a GOV fail-closed gate. Speed and safety are orthogonal controls, never traded against each other.

---

*HITL v1.0 · Module ⑧ of the Prospect Dominion Elite Edge · house style aligned with GOV ⑦ and the Workflow Suite Index · presentation layer specified in UI-SPEC v1.0 · resolves GOV's `cockpit-svc` bridge and WL2-6's promotion queue.*
