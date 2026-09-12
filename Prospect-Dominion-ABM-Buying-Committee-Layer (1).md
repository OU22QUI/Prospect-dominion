# 🕸️ Prospect Dominion — ABM & Buying-Committee Play Orchestration

> **Module ⑩ · ABM v1.0 · Elite Edge Layer**
> Everything upstream treats the **contact** as the unit of work. Enterprise deals are not won by contacts — they are won by *committees*. This module upgrades the unit of work from a person to an **account graph**, and replaces the sequence with a **play**: a multi-threaded, role-aware, state-machine campaign run across every human who touches the decision.

---

## §A.0 — Why This Module Exists

Dominion's executable pipeline (WG2 → WL2-6) is a **single-threaded** machine: one lead, one thread_id, one conversation, one booking. That is correct for SMB/self-serve motion and structurally insufficient above ~€25k ACV, where:

- **5.4–11 people** sign off. A single champion who goes dark kills the deal silently.
- The person who **replies** is rarely the person who **buys**. Reply-optimized targeting systematically selects for low-authority contacts.
- Signals are **account-level** (funding, hiring, stack change) but scoring is contact-level — the signal's value is diluted across the wrong people.
- Losses are attributed to the contact, so WL2-6 learns the wrong lesson: it blames the message when the real failure was *never reaching the economic buyer*.

ABM fixes all four by making the **account the primary entity**, the **committee the target**, and the **play the campaign**. Neo4j — already in the DATA layer — becomes the runtime, not just a store.

---

## §A.1 — Layer Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  A6  PLAY RUNNER        Account state machine · multi-thread cadence   │
├──────────────────────────────────────────────────────────────────────┤
│  A5  ORCHESTRATION      Sequencing rules · thread interlock · pacing   │
├──────────────────────────────────────────────────────────────────────┤
│  A4  MESSAGE STRATEGY   Role-specific narrative · consistency spine    │
├──────────────────────────────────────────────────────────────────────┤
│  A3  COMMITTEE MODEL    Role inference · champion/blocker/EB scoring   │
├──────────────────────────────────────────────────────────────────────┤
│  A2  ACCOUNT GRAPH      Neo4j entities · edges · coverage topology     │
├──────────────────────────────────────────────────────────────────────┤
│  A1  ACCOUNT RESOLUTION Entity resolution · hierarchy · dedup          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## §A.2 — Squads

| Squad | Owns | Runtime |
|---|---|---|
| **Resolution Squad** | collapses domains, subsidiaries, and aliases into one canonical account; parent/child hierarchy | `account-svc` |
| **Committee Squad** | infers roles, seniority, and function; assigns Champion / Economic Buyer / Blocker / Influencer / Coach; computes coverage | `committee-svc` (CrewAI) |
| **Graph Squad** | maintains the Neo4j account graph; serves traversal queries (who reports to whom, who touches whom) | `graph-svc` (Neo4j) |
| **Play Squad** | runs the account state machine; decides next thread, next role, next channel, next beat | `play-svc` (n8n + Mastra) |
| **Narrative Squad** | generates role-specific messaging off one shared account thesis; enforces cross-thread consistency | `narrative-svc` (LiteLLM) |
| **Signal Squad** | routes account-level signals to the right committee member, not the loudest one | shares WG2 ingress |

---

## §A.3 — Account Resolution (A1) — the prerequisite

Nothing works until "Acme", "acme.com", "Acme Holdings BV", and "acme.co.uk" are **one node**.

| Step | Method |
|---|---|
| **Canonicalization** | registrable domain + normalized legal name + registry lookup |
| **Hierarchy** | parent ↔ subsidiary edges from registries, footers, MX/DNS shared infrastructure |
| **Alias merge** | fuzzy name match gated by a shared hard identifier (domain, registration number) — never name alone |
| **Dedup guard** | merge only on ≥2 corroborating identifiers; ambiguous merges escalate to Cockpit (Module ⑧) |
| **Territory rule** | one account = one owner = one play. Prevents two threads pitching the same company differently. |

> **Invariant:** a contact cannot enter a play until it is bound to a resolved account node. Unresolved contacts fall back to the single-thread pipeline.

---

## §A.4 — The Account Graph (A2) — Neo4j as runtime

**Nodes:** `Account`, `Person`, `Role`, `Signal`, `Play`, `Thread`, `Touch`, `Meeting`, `Opportunity`.

**Edges:**

| Edge | Meaning |
|---|---|
| `(:Person)-[:WORKS_AT]->(:Account)` | employment, with confidence + as-of date |
| `(:Person)-[:REPORTS_TO]->(:Person)` | inferred org line |
| `(:Person)-[:PEER_OF]->(:Person)` | same function, same level |
| `(:Person)-[:OWNS_BUDGET_FOR]->(:Category)` | economic authority |
| `(:Signal)-[:AFFECTS]->(:Account)` | account-level trigger |
| `(:Play)-[:TARGETS]->(:Account)` | active orchestration |
| `(:Thread)-[:ENGAGES]->(:Person)` | live conversation (links to pipeline `thread_id`) |
| `(:Person)-[:INTRODUCED_BY]->(:Person)` | warm path — the seam to Module ⑬ |

**Coverage query** — the single most valuable traversal in the system: *given an account, which committee roles are unengaged, and which known person is the shortest path to each?*

---

## §A.5 — The Committee Model (A3)

| Role | Definition | Detection signals |
|---|---|---|
| **Champion** | wants the change, will spend internal capital | positive reply sentiment, content engagement, asks forward-looking questions, forwards internally |
| **Economic Buyer** | controls the budget line | seniority + function + budget-ownership inference; often never replies |
| **Technical Evaluator** | judges feasibility | title/function match to the stack signal that triggered the account |
| **Blocker** | loses from the change | incumbent-vendor owner, status-quo owner, adjacent-team lead |
| **Coach** | leaks internal context without buying | replies helpfully but disclaims authority |
| **End User** | feels the pain daily | function match, high volume, low seniority |

**Committee Coverage Score (CCS)** — the account's true health metric, replacing "did the lead reply":

```
CCS = Σ (role_weight × engagement_depth × recency_decay)  /  Σ role_weight
```

Weights are ICP-derived (learned from closed-won committee shapes in WL2-6), not hard-coded. **A single-threaded account is a red account, regardless of how warm the one thread feels.** This is the module's central claim.

---

## §A.6 — Play Runner (A6) — the account state machine

A **play** is a versioned, event-driven state machine over an account. Its states:

| State | Meaning | Exit condition |
|---|---|---|
| `S0 · Dormant` | resolved account, no active trigger | qualifying signal fires |
| `S1 · Triggered` | account-level signal validated | committee mapped to minimum coverage |
| `S2 · Mapping` | discovering + verifying committee members | ≥ N roles identified (N from play template) |
| `S3 · Multi-Thread` | parallel threads opening across roles, paced | first meaningful engagement |
| `S4 · Champion-Building` | one thread reciprocating; deepen + arm them | champion confirms + names others |
| `S5 · Committee-Expansion` | champion-led + direct expansion to EB/evaluator | CCS ≥ threshold |
| `S6 · Consensus` | multi-role engagement; group meeting sought | meeting booked (hands to FLOW-WV) |
| `S7 · Won / Lost / Dormant` | terminal | outcome ingested (hands to FLOW-WL1) |

**Play templates** are declarative YAML: entry criteria, required roles, thread sequencing, pacing, channel policy, escalation, exit gates. Templates are versioned artifacts — like ICP-as-Code, plays are **plays-as-code**.

---

## §A.7 — Thread Interlock (A5) — the hard part

Multi-threading fails when the committee compares notes and finds three inconsistent pitches. The interlock rules:

1. **One account thesis.** All threads derive from a single generated account narrative (the *why now* for this company). Role messages are *projections* of it, never independent inventions.
2. **Pacing law.** No two threads to the same account open within the same window; total account touch volume is capped, not per-contact capped. Prevents the "your whole team just got emailed" moment.
3. **Awareness rule.** Once a champion is confirmed, all *new* threads are disclosed as company-level outreach, and existing threads are told about the champion where appropriate — never covertly parallel.
4. **Deconfliction.** If two contacts reply, the play collapses to the higher-authority thread and switches the other to a supporting narrative.
5. **Escalation etiquette.** Never approach the economic buyer *over* an engaged champion without champion-routed permission or an explicit template rule.
6. **Blocker containment.** Detected blockers are not pitched; the play routes around them and arms the champion with counter-narrative.

> **Governance seam:** every play-generated message still passes the §G.3 Send Gate. The account thesis itself is a grounded artifact — its claims cite signals in the provenance store.

---

## §A.8 — Signal Routing at Account Level

WG2 emits `lead.discovered` per contact. ABM adds `account.signal.detected`, and the Signal Squad answers: *given this signal, which committee role should hear about it?*

| Signal | Routes to | Narrative angle |
|---|---|---|
| Funding round | Economic Buyer | capacity + mandate to invest |
| Competitor tool in job post | Technical Evaluator | migration/comparison |
| New exec hire | that exec (Champion candidate) | 90-day mandate |
| Hiring surge in a function | that function's leader | scale pain |
| Stack change | Technical Evaluator + End User | integration reality |
| Compliance/regulatory event | Blocker-turned-Champion (risk owner) | risk reduction |

The same signal produces **different messages to different people** — which is exactly what a contact-level pipeline cannot do.

---

## §A.9 — Event Contracts

**Consumes:** `lead.discovered` (WG2), `lead.enriched` / `lead.scored` (W2), `reply.classified` (W5), `meeting.booked` (WV), `meeting.won` / `meeting.lost` (WL1).

**Emits:**

| Event | Payload highlights | Consumer |
|---|---|---|
| `account.resolved` | canonical account, hierarchy, member count | graph, play-svc |
| `account.signal.detected` | signal, target role, decay | play-svc |
| `committee.mapped` | roles, gaps, CCS | play-svc, Cockpit |
| `play.started` / `play.state.changed` | play id, version, state transition, reason | Cockpit, audit |
| `thread.opened` | thread_id, person, role, account_id | WO1 (dispatch) |
| `champion.identified` | person, confidence, evidence | play-svc, Cockpit |
| `blocker.detected` | person, evidence | play-svc, narrative-svc |
| `coverage.gap` | missing roles, suggested paths | Cockpit, Module ⑬ |
| `play.completed` | terminal state, committee shape at close | WL1/WL2-6 |

**Contract extension:** every pipeline `thread_id` now also carries `account_id` and `play_id`. This is the one change required in existing workflows — it is additive and backward-compatible; unresolved contacts simply carry null play context.

---

## §A.10 — Learning Seam (into WL2-6)

ABM makes the learning loop dramatically smarter, because it supplies **committee-shaped labels**:

- **Winning committee shape** — closed-won accounts reveal which role combinations actually convert. Feeds role weights in CCS.
- **Coverage-to-win curve** — what CCS threshold predicts a won deal. Becomes the S5→S6 exit gate.
- **Role-message attribution** — which narrative angle moved which role. Feeds copy models per role, not per persona-blob.
- **Loss diagnosis** — distinguishes *"wrong message"* from *"never reached the economic buyer."* This single distinction repairs the most damaging mislabeling in the whole flywheel.
- **Play version A/B** — plays are versioned, so play templates themselves enter the eval + promotion pipeline (§G.4 gate applies).

---

## §A.11 — Roadmap

- **Phase 0 — Resolution & graph.** `account-svc` + Neo4j account/person/role nodes; `account_id` added to the thread contract. *Exit: every contact resolves to one canonical account.*
- **Phase 1 — Committee mapping.** Role inference + CCS; coverage gaps surfaced in the Cockpit. *Exit: every active account has a visible committee map.*
- **Phase 2 — Play runner (read-only).** State machine runs in shadow, recommends next thread; human executes. *Exit: recommendations match rep judgment ≥80%.*
- **Phase 3 — Multi-thread live.** Play-driven dispatch with pacing + interlock enforced; Autonomy Dial at A1 (approve). *Exit: no account over-touch incidents.*
- **Phase 4 — Learning.** Committee-shaped labels into WL2-6; play templates versioned and eval-gated. *Exit: CCS threshold empirically predicts win rate.*

---

## §A.12 — Elite Differentiators

- **The account is the unit, the committee is the target.** Every competing tool optimizes for reply rate from one person; Dominion optimizes for *coverage of the people who actually decide*.
- **Plays-as-code.** Campaigns are versioned, testable, promotable artifacts under the same eval and governance gates as models — not sequences someone hand-built and forgot.
- **One thesis, many projections.** Multi-threading without contradiction: every role hears a different message that is provably the same argument.
- **Consensus engineering, not spray.** Pacing laws, escalation etiquette, and blocker containment mean the machine multi-threads the way a disciplined enterprise rep does — not the way a blast tool does.
- **It fixes the flywheel's blind spot.** By separating "bad message" from "wrong human," ABM stops the learning loop from optimizing copy to solve a coverage problem.
- **The graph you own.** The full relationship topology of every account you have ever touched lives in your Neo4j — and it is the substrate for Module ⑬'s warm-intro engine.

---

*ABM v1.0 · Module ⑩ of the Prospect Dominion Elite Edge · extends the thread contract with `account_id` + `play_id` · consumes WG2/W2/W5/WV/WL1 · feeds WL2-6 · gated by GOV §G.3 and §G.4 · surfaced in Cockpit (Module ⑧).*
