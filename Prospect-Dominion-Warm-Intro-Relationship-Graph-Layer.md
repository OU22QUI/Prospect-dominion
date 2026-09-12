# 🤝 Prospect Dominion — Warm-Intro & Relationship Graph Layer

> **Module ⑬ · WIR v1.0 · Elite Edge Layer · Final module of the Elite Edge**
> Everything upstream makes cold outreach as warm as cold can get. This module asks the question the rest of the system cannot: **does it have to be cold at all?** WIR mines the organization's own accumulated relationship capital — colleagues, alumni, investors, customers, advisors, past conversations — finds the shortest credible human path into a target account, and orchestrates the ask. A referred prospect converts at multiples of a cold one. The graph that finds them is an asset that only compounds, and only if you own it.

---

## §W.0 — Why This Module Exists

Dominion's economics are already strong at the cold end. But three structural facts make this the highest-ROI module in the entire corpus:

- **The relationship capital already exists and is invisible.** Every founder, rep, advisor, and investor in the organization carries a network. It lives in scattered inboxes, phones, and memories. No one can answer *"who do we know at Acme?"* — so nobody asks, and the asset is never used.
- **Warm paths beat every optimization above them.** No amount of signal-first targeting, psychographic tuning, or microsite personalization matches an introduction from someone the buyer already trusts. It is the one lever that changes the conversion regime rather than the conversion rate.
- **⑩ already produces the demand for it.** The `coverage.gap` event asks *"who is the shortest path to this unengaged economic buyer?"* — and today has nowhere to send the question. WIR is the answer.

**And the sovereignty argument is sharpest here.** Every commercial relationship-intelligence tool requires you to upload your team's entire inbox and contact history to a third party. That is the most sensitive data an organization has. Dominion computes the same graph on the client's own metal, and nobody else ever sees it.

---

## §W.1 — Layer Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  W6  ASK ORCHESTRATION  Intro request · draft · nudge · handoff        │
├──────────────────────────────────────────────────────────────────────┤
│  W5  PATH ENGINE        Shortest credible path · multi-hop · ranking   │
├──────────────────────────────────────────────────────────────────────┤
│  W4  STRENGTH MODEL     Tie strength · recency · reciprocity · trust   │
├──────────────────────────────────────────────────────────────────────┤
│  W3  RELATIONSHIP GRAPH Neo4j edges · people ↔ people ↔ accounts       │
├──────────────────────────────────────────────────────────────────────┤
│  W2  CONSENTED INGEST   Per-connector opt-in · metadata-only harvest   │
├──────────────────────────────────────────────────────────────────────┤
│  W1  NETWORK REGISTRY   Whose networks · what scope · what boundaries  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## §W.2 — Squads

| Squad | Owns | Runtime |
|---|---|---|
| **Consent Squad** | per-person, per-connector opt-in; scope boundaries; revocation | `wir-consent` (bridges §G.1) |
| **Ingest Squad** | metadata-only harvest from consented sources; normalization; dedup | `wir-ingest` |
| **Graph Squad** | maintains relationship edges in Neo4j alongside the ⑩ account graph | `graph-svc` (Neo4j) |
| **Strength Squad** | computes tie strength, decay, reciprocity, and trust class | `wir-strength` |
| **Path Squad** | multi-hop traversal; ranks candidate paths by likelihood-to-convert | `wir-path` |
| **Ask Squad** | drafts the intro request + the forwardable blurb; runs nudges; tracks outcome | `wir-ask` (CrewAI + LiteLLM) |

---

## §W.3 — Network Registry & Consent (W1–W2) — the gate before anything

> **This module does not start with data. It starts with permission.** Mining a colleague's network without their explicit, scoped, revocable consent is both a legal exposure and a fast way to destroy internal trust. WIR is consent-first by construction.

| Control | Rule |
|---|---|
| **Per-person opt-in** | each network owner opts in individually. No org-wide default, ever. |
| **Per-connector scope** | separate consent for each source; opting into one is not opting into all |
| **Metadata-only** | **email/message *bodies* are never ingested.** Only: counterparty address, direction, timestamp, thread id. Content stays untouched. |
| **Exclusion lists** | owners exclude domains, individuals, and whole categories (personal, medical, legal, family) before first ingest |
| **Visibility tiers** | owner sees their full graph; the org sees only *"a path exists via {owner}"* until the owner approves disclosure |
| **Revocation** | one action purges that owner's edges from the graph and all derived paths, immediately |
| **Audit** | every ingest, path query, and disclosure writes to the ledger (§G.5) |

**Consented sources:** colleague mailbox metadata · calendar attendee history · CRM contact/activity history · LinkedIn connections (owner-exported, not scraped) · past-customer and champion alumni records · investor/advisor networks · Dominion's own conversation history (every prospect ever spoken to) · community/alumni rosters the org legitimately holds.

---

## §W.4 — The Relationship Graph (W3)

Extends the ⑩ account graph — **same Neo4j, one topology**. That unification is the point: account structure and human trust in a single traversable substrate.

**Edges added:**

| Edge | Source | Meaning |
|---|---|---|
| `(:Person)-[:KNOWS {strength, last_contact, channel_count, reciprocity}]->(:Person)` | ingest | the core tie |
| `(:Person)-[:WORKED_WITH {org, overlap_years}]->(:Person)` | employment history | colleague trust — durable |
| `(:Person)-[:ALUMNI_OF]->(:Org)` | education/employment | weak but real affinity |
| `(:Person)-[:INVESTED_IN]->(:Account)` | investor records | high-leverage, high-cost |
| `(:Person)-[:WAS_CUSTOMER_OF]->(:Account)` | CRM | credible peer reference |
| `(:Person)-[:ADVISES]->(:Account)` | disclosures | strong, scarce |
| `(:Person)-[:SPOKE_WITH]->(:Person)` | **Dominion's own history** | our compounding asset |
| `(:Person)-[:INTRODUCED_BY]->(:Person)` | ask outcomes | closes the loop from ⑩ |

> **The compounding clause:** every conversation Dominion ever has — won, lost, or ghosted — deposits an edge. A prospect who said "not now" two years ago is a *warm node* today. This graph is worthless on day one and close to irreplaceable in year three. It is the strongest lock-in a sovereign system can offer a client, because the client owns it outright.

---

## §W.5 — Tie Strength Model (W4)

Not all connections are usable. A LinkedIn connection from 2014 is not a path.

```
S = w₁·frequency + w₂·recency_decay + w₃·reciprocity
  + w₄·channel_diversity + w₅·relationship_class + w₆·context_overlap
```

| Component | Signal |
|---|---|
| **frequency** | interaction count over trailing window |
| **recency_decay** | exponential; a tie untouched for 24 months is nearly dead |
| **reciprocity** | **bidirectional exchange — the strongest single predictor.** One-way outreach is not a relationship |
| **channel_diversity** | email + calendar + meeting > email alone |
| **relationship_class** | worked-with > customer > investor > advisor > event > alumni > connection |
| **context_overlap** | shared employer, project, or deal history |

**Trust classes** — the actionable output:

| Class | Meaning | Ask policy |
|---|---|---|
| **T1 Strong** | recent, reciprocal, multi-channel | direct ask; high yield |
| **T2 Warm** | real history, some decay | ask with a re-warm preamble |
| **T3 Dormant** | genuine once, long cold | re-engage first; **never** open with a favor |
| **T4 Weak** | one-way or credential-only | do not ask; use as context only |

> **Doctrine:** asking a T3/T4 tie for an introduction spends more social capital than it generates and can damage the owner's relationship. WIR enforces this — it will withhold a path rather than burn a tie.

---

## §W.6 — Path Engine (W5)

**Query:** *given a target person in a target account, return the ranked set of credible paths from anyone in our consented network.*

```
PathScore = Π(edge_strength) × hop_penalty × broker_willingness
          × target_receptivity × freshness × path_scarcity_bonus
```

| Factor | Note |
|---|---|
| **hop_penalty** | 1 hop ≫ 2 hops ≫ 3. **3+ hops are not offered** — an intro chain longer than two people does not survive contact with reality |
| **broker_willingness** | learned per broker: historical accept rate, current ask-load, stated preferences |
| **target_receptivity** | seniority gap, prior Dominion contact history, current signal heat |
| **path_scarcity_bonus** | if only one path exists to a critical role, it is precious — spend it deliberately |

**Ask-load governor:** each broker has a rate limit (e.g. 2 asks/month). The system will *not* over-mine a generous colleague. It also cools down after a decline. Relationship capital is a finite, renewable resource, and WIR treats it like one — this is the difference between a referral engine and a friendship-shredder.

**⑩ integration:** on every `coverage.gap`, WIR runs the query for each missing committee role and returns paths. The play runner then chooses per role: warm path (if T1/T2 exists) or cold thread. **Warm always preempts cold** — and any cold thread already open to that person is paused, never run in parallel with an intro.

---

## §W.7 — Ask Orchestration (W6)

The mechanics of the ask determine whether it happens. WIR makes saying yes nearly frictionless.

**Flow:**

1. **`intro.path.found`** → the *broker* (not the prospect) is contacted, internally.
2. **The ask** is short, specific, and pre-justified: who, why them, why now, and an explicit *"no is completely fine"*.
3. **The forwardable blurb** — the critical artifact. A 3–4 sentence, ready-to-send paragraph the broker can forward *unedited*, written in the broker's register, grounded in the target's real signals (§G.3 applies), with the ⑫ microsite link attached where appropriate.
4. **Double opt-in default.** The broker asks the target's permission before disclosing contact details. Slower, materially higher conversion, and it protects the broker's relationship — which is the asset being borrowed.
5. **Verdict:** accept → `intro.made` → the thread opens **warm** (WO1 uses a distinct warm cadence: slower, more deferential, referencing the broker); decline or silence → one nudge at day 5, then closed permanently. **No second nudge, ever.**
6. **Loop closure:** the outcome trains `broker_willingness`, and a successful intro writes `(:Person)-[:INTRODUCED_BY]->(:Person)` — enriching the graph that produced it.
7. **Thank-you obligation.** On a won deal, the broker is credited and notified. Reciprocity is what keeps the well full.

**Warm-thread rules:** a referred prospect never enters standard cold cadence. Different pacing, different tone, no aggressive follow-up, and a hard stop — mishandling a referral costs the broker's relationship, not just a lead.

---

## §W.8 — Event Contracts

**Consumes:** `coverage.gap` / `committee.mapped` / `account.resolved` (⑩), `lead.scored` (W2), `meeting.won` / `meeting.lost` (WL1), consent-registry changes.

**Emits:**

| Event | Payload | Consumer |
|---|---|---|
| `network.ingested` | owner, connector, edge count, scope | graph, audit |
| `intro.path.found` | target, ranked paths, brokers, trust class | ⑩ play runner, Cockpit ⑧ |
| `intro.requested` | broker, target, blurb id | Cockpit, audit |
| `intro.accepted` / `intro.declined` | verdict, latency | ask-model, ⑩ |
| `intro.made` | new warm thread_id, broker, account_id | **WO1 (warm cadence)**, ⑩ |
| `warm.thread.opened` | thread_id, provenance = referral | W5, scoring |
| `broker.load.exceeded` | broker, window | ask governor |
| `network.revoked` | owner, purge confirmation | graph, audit |

**Contract extension:** threads gain `origin ∈ {cold, warm, referral}` and optional `broker_id`. WL2-6 can then compare cold vs. warm conversion natively — which is how the org learns what its network is actually worth in revenue.

---

## §W.9 — Governance Seam

- **Consent is the entry gate** (§G.1). No ingest without per-person, per-connector opt-in; revocation purges immediately and verifiably.
- **Metadata-only** ingest is a hard architectural boundary, not a setting. Message bodies are never read.
- **Every path query is logged** (§G.5). Who asked to see whose network, and when, is auditable — this is what makes internal adoption possible.
- **Forwardable blurbs pass the Send Gate** (§G.3): grounded, no invented claims, no fabricated familiarity.
- **Kill switch** (§G.7) halts all intro asks instantly without touching the graph.
- **DSAR cascade:** an erasure request removes the person as node *and* as broker across all derived paths.
- **Autonomy Dial (⑧):** intro asks default to **A1 (human approves)** even in an otherwise-autonomous deployment. An AI should not spend a human's social capital unsupervised. This is a deliberate, permanent exception.

---

## §W.10 — Roadmap

- **Phase 0 — Consent & registry.** Opt-in flows, scope controls, exclusion lists, revocation. *Exit: at least one owner has opted in with full control and understands exactly what was taken.*
- **Phase 1 — Graph & strength.** Metadata ingest, edge construction, tie-strength scoring, trust classes. *Exit: the system can answer "who do we know at Acme, and how well?"*
- **Phase 2 — Path engine.** 1–2 hop ranked paths wired to ⑩ `coverage.gap`; surfaced in the Cockpit. *Exit: every coverage gap is checked for a warm path before a cold thread opens.*
- **Phase 3 — Ask orchestration.** Broker asks, forwardable blurbs, double opt-in, load governor, warm cadence in WO1. *Exit: intros are requested, tracked, and closed the loop on.*
- **Phase 4 — Learning & compounding.** Broker-willingness model, warm-vs-cold conversion analytics into WL2-6, Dominion conversation history auto-deposited as edges. *Exit: the graph measurably improves every quarter without manual curation.*

---

## §W.11 — Elite Differentiators

- **It changes the regime, not the rate.** Every other module makes cold outreach better. This one replaces cold outreach with trust — the only lever that moves conversion by multiples.
- **The most sensitive graph in the business, computed on your own metal.** Commercial relationship tools require uploading your team's entire inbox to a vendor. Dominion never lets that data leave the building. For many buyers this is the difference between deploying and declining.
- **Consent-first, metadata-only, revocable.** The design makes internal adoption possible — colleagues opt in because the boundaries are architectural, not promised.
- **It refuses to burn relationships.** Ask-load governors, dormant-tie protection, single-nudge limits, double opt-in, and permanent human approval. The system treats social capital as the finite asset it is — which is precisely why it keeps working past month three.
- **Every conversation compounds.** Won, lost, or ghosted, each dialogue deposits an edge. The asset appreciates with use and is fully portable to the client — the strongest form of lock-in a sovereign product can honestly offer.
- **It answers ⑩'s hardest question.** "The economic buyer is unengaged — now what?" Cold-only systems have no answer. Dominion returns a ranked list of humans who can open the door.

---

*WIR v1.0 · Module ⑬ of the Prospect Dominion Elite Edge · final module · shares the Neo4j graph with ⑩ · consumes `coverage.gap` · feeds WO1 warm cadence and WL2-6 origin analytics · consent-gated by GOV §G.1, logged to §G.5, permanently A1 in Cockpit ⑧.*
