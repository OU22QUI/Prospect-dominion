# 🛡️ Prospect Dominion — Governance & Trust Control Plane

> **Module ⑦ · GOV v1.0 · Elite Edge Layer**
> The always-on safety spine that lets Dominion run autonomously without running amok. Every outbound word, every model promotion, and every data-subject obligation passes through here. This is the module that turns "a working pipeline" into "a system a regulated buyer will actually deploy."

---

## §G.0 — Why This Module Exists

The executable layer (WG2 → WL2-6) is now complete and *self-improving*. That is precisely the danger: a system that writes its own copy, redirects its own targeting, and sends at scale will, without a control plane, eventually hallucinate a claim, email a suppressed contact, or promote a drifted model into production. Two flows already **call into governance but have no home for it**:

- **W5 · Conversation Loop** posts every AI reply draft to `governance-svc:8080/gate` (`checks: grounding, unsubscribe, claims, tone`) before send.
- **WL2-6 · Learning Flywheel** routes every high-impact model change through a **human-gated promotion** with an explainable-delta packet.

GOV is where those calls resolve. It is not a workflow — it is a **control plane**: a set of always-on services, a policy store, an immutable audit ledger, and one global kill switch.

---

## §G.1 — Layer Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  G6  KILL PLANE        Global + scoped kill switches · circuit breakers │
├──────────────────────────────────────────────────────────────────────┤
│  G5  AUDIT LEDGER      Append-only, hash-chained · provenance · replay  │
├──────────────────────────────────────────────────────────────────────┤
│  G4  HUMAN GATES       Promotion gate · Tier-1 approval · escalation    │
├──────────────────────────────────────────────────────────────────────┤
│  G3  SEND GATE         Grounding · claims · brand-safety · tone · legal │
├──────────────────────────────────────────────────────────────────────┤
│  G2  POLICY STORE      Versioned policy-as-code · region rules · lists  │
├──────────────────────────────────────────────────────────────────────┤
│  G1  IDENTITY & CONSENT Lawful-basis registry · suppression · DSAR      │
└──────────────────────────────────────────────────────────────────────┘
```

Everything above the Policy Store reads from it; everything writes to the Audit Ledger; the Kill Plane can freeze any layer.

---

## §G.2 — Squads

| Squad | Owns | Runtime |
|---|---|---|
| **Grounding Squad** | fact-verification of every claim in a draft against provenance store | `governance-svc` (cross-encoder + retrieval) |
| **Brand-Safety Squad** | tone, prohibited claims, forbidden phrasing, competitor-disparagement | `governance-svc` (classifier + rule set) |
| **Consent Squad** | suppression, lawful-basis tagging, region opt-in, DSAR/deletion | `compliance-svc` |
| **Ledger Squad** | writes the hash-chained audit trail; serves replay + provenance queries | `audit-svc` (append-only Postgres + object store) |
| **Kill-Switch Squad** | evaluates circuit-breaker thresholds; owns the freeze API | `killswitch-svc` |
| **Human-Gate Squad** | renders explainable-delta packets to the Rep Cockpit; records verdicts | `cockpit-svc` bridge |

---

## §G.3 — The Send Gate (G3) — resolves W5's `governance-svc/gate`

Every draft that any module intends to send **must** POST to the gate and receive `pass: true` before dispatch. The gate is deterministic, ordered, and fail-closed.

| # | Check | Method | Fail action |
|---|---|---|---|
| 1 | **Grounding** | every factual assertion must map to a real datum in the provenance store (signal, account fact, thread history) via retrieval + cross-encoder score ≥ τ | reject → Cockpit Tier-1 |
| 2 | **Claims** | no unverifiable promises (pricing, guarantees, ROI figures) unless drawn from an approved claim library | reject → Cockpit Tier-1 |
| 3 | **Unsubscribe** | opt-out mechanism + physical address present (email); STOP honored (SMS) | reject → auto-repair, re-check once |
| 4 | **Brand-safety / tone** | classifier vs. psychographic tone target; no disparagement, no prohibited phrasing | reject → Cockpit Tier-1 |
| 5 | **Legal / region** | region-aware opt-in satisfied; contact not suppressed; lawful basis present | reject → suppress + flag |

> **Fail-closed invariant:** if `governance-svc` is unreachable or times out, the gate returns `pass: false`. **Nothing auto-sends on gate failure.** Silence is safe; an ungoverned send is not.

**Response contract**

```json
{
  "pass": false,
  "thread_id": "…",
  "failed_checks": ["grounding"],
  "evidence": { "grounding": { "unsupported_span": "…", "max_score": 0.41, "tau": 0.62 } },
  "route": "cockpit_tier1",
  "audit_id": "gov_01J…"
}
```

---

## §G.4 — The Promotion Gate (G4) — resolves WL2-6's human gate

WL2-6 classifies model changes by blast radius. GOV owns the **high-impact** path.

| Impact | Path | Examples |
|---|---|---|
| **Low-risk** | auto-promote, logged | copy variant reweight, cadence timing nudge |
| **High-impact** | **human-gated** — explainable-delta packet → Rep Cockpit → one-click approve/reject → `audit-svc` | ICP centroid diff, scoring-model swap, persona remap |

**Explainable-delta packet** (rendered to the operator, never a raw diff):
- *What changed* (plain language) · *Why* (attribution evidence from WL2) · *Expected effect* (shadow-eval metrics from WL5) · *Blast radius* (accounts/behaviors affected) · *Rollback* (one-click revert to prior version).

On approve → emit `model.promoted` (WL6 begins drift-watching the new champion) and write the verdict + operator identity to the ledger. On reject → challenger retired, reason logged.

---

## §G.5 — Identity & Consent (G1)

| Control | Rule |
|---|---|
| **Global suppression list** | honored across *all* channels (email, SMS, voice, LinkedIn); checked at the Send Gate and at WO1 eligibility (O-0) |
| **Lawful-basis registry** | every contact carries a basis tag (legitimate-interest / consent / contract) + region; region-aware opt-in enforced |
| **Instant opt-out** | W5 suppresses on `negative`/STOP in real time; propagates to suppression list within the same event |
| **DSAR & deletion** | data-subject-access and right-to-erasure workflows; deletion cascades across Postgres, Qdrant, Mem0, Neo4j, and object store; certificate written to ledger |
| **Provenance** | every sourced datum stores `source` + `sourced_at`; recon respects robots/ToS; no datum enters a prompt without provenance |

---

## §G.6 — Audit Ledger (G5)

- **Append-only + hash-chained.** Each entry stores the prior entry's hash → tamper-evident; any gap or edit is detectable.
- **Every send** records the *exact prompt + retrieved context + model version + gate verdict* that produced it (Langfuse trace id + Postgres row).
- **Every model promotion** records the delta packet, operator identity, and timestamp.
- **Every consent event** (opt-out, DSAR, deletion) records the request, action, and certificate.
- **Replay:** any past decision can be reconstructed from the ledger for a regulator, a client audit, or a post-mortem.

> **Sovereign guarantee:** the ledger lives entirely in the client's Postgres + Garage/object store. No third party holds the record of what the system did.

---

## §G.7 — Kill Plane (G6)

| Scope | Trigger | Effect |
|---|---|---|
| **Global** | operator command | freezes all sends, all dispatchers, all promotions — instantly, fail-closed |
| **Channel** | deliverability breach (bounce/spam-rate threshold) | freezes one channel; others continue |
| **Domain / pool** | reputation drop (W7 health) | quarantines a sending domain; traffic reroutes |
| **Model** | drift alarm from WL6 | auto-rolls back to prior champion version |
| **Account** | complaint / legal hold | suppresses one account across every module |

Circuit breakers are **automatic** (threshold-driven) with a **manual master switch** always available in the Cockpit. Every trip writes to the ledger and notifies the operator.

---

## §G.8 — Event Contracts

**Consumes** (subscribes): `draft.ready` (from W5/WO1), `model.change.proposed` (from WL2-6), `reply.negative` (from W5), `dsar.requested`, `deliverability.breach` (from W7), `drift.detected` (from WL6).

**Emits**: `gate.passed` / `gate.failed`, `model.promoted` / `model.rejected`, `contact.suppressed`, `dsar.completed`, `killswitch.tripped`, `audit.written`.

All events carry the shared `thread_id` contract from the Workflow Suite Index, so a governance verdict is traceable back to the exact prospect lifecycle that triggered it.

---

## §G.9 — Service Endpoints (wire to INFRA v1.0)

| Service | Role |
|---|---|
| `governance-svc:8080` | Send Gate (grounding + claims + brand-safety + tone) |
| `compliance-svc` | consent, suppression, region rules, DSAR/deletion |
| `audit-svc` | append-only hash-chained ledger + provenance/replay API |
| `killswitch-svc` | circuit breakers + global freeze API |
| `cockpit-svc` | human-gate rendering + verdict capture (Module ⑧ bridge) |

All are placeholders mapping to docker-compose service names in **INFRA v1.0**.

---

## §G.10 — Roadmap

- **Phase 0 — Fail-closed spine.** Stand up `governance-svc` with grounding + unsubscribe checks; wire W5 to it; ledger writes on every send. *Exit: nothing sends without a logged verdict.*
- **Phase 1 — Consent & kill.** Suppression + lawful-basis registry; global + channel kill switches; W7 → domain quarantine. *Exit: one switch freezes the system; opt-outs propagate instantly.*
- **Phase 2 — Human promotion gate.** Explainable-delta packets → Cockpit; WL2-6 high-impact path live. *Exit: no high-impact model change reaches prod unapproved.*
- **Phase 3 — Full auditability & DSAR.** Hash-chaining, replay API, cascade deletion, drift auto-rollback. *Exit: a regulator can replay any decision; a subject can be erased across all stores.*

---

## §G.11 — Elite Differentiators

- **Fail-closed by construction.** Every gate defaults to *deny* on error. The system's resting state is safe; sending is the privileged action, not the default.
- **Grounded or silent.** No claim reaches a prospect unless it maps to a real, provenance-backed datum — hallucination is structurally blocked, not merely discouraged.
- **Velocity with a seatbelt.** Low-risk learning auto-promotes; only high-blast-radius changes wait for a human — the flywheel keeps spinning without becoming reckless.
- **Tamper-evident sovereignty.** The complete record of what the machine said and did lives in the client's own hash-chained ledger — auditable by them, owned by them, held by no one else.
- **One switch.** A single operator action freezes an autonomous, self-improving, multi-channel outbound machine in its tracks. That is what makes it safe to turn on.

---

*GOV v1.0 · Module ⑦ of the Prospect Dominion Elite Edge · house style aligned with FLOW-WG2…WL2-6 and the Workflow Suite Index · resolves the Governance gate (W5) and Promotion gate (WL2-6).*
