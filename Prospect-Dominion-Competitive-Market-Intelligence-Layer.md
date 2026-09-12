# 🎯 Prospect Dominion — Competitive & Market Intelligence Layer

> **Module ⑪ · CMI v1.0 · Elite Edge Layer**
> Dominion already knows everything about the **prospect**. It knows nothing about the **alternatives the prospect is weighing**. CMI closes that blind spot: it watches the competitive field continuously, detects displacement windows, arms every message and every human with current battlecards, and — critically — learns from *why deals were actually lost*, not from what the rep typed into a dropdown.

---

## §C.0 — Why This Module Exists

Every deal in the pipeline is a comparison, whether or not the system participates in it. Four concrete failures today:

- **Competitor mentions in replies are handled generically.** W5 classifies intent, not *which vendor* the prospect named. The single highest-leverage moment in outbound — "we already use X" — is answered with a template.
- **Displacement windows are invisible.** A competitor's price rise, outage, acquisition, or security incident is the strongest buying trigger that exists, and WG2 does not hunt for it.
- **Loss reasons are unstructured.** WL1 ingests won/lost; without competitive attribution, WL2-6 cannot learn *which competitor beats us, in which segment, on which axis*.
- **Battlecards rot.** Any human-maintained competitive doc is stale within a quarter. Reps then either improvise or say nothing.

CMI turns the competitive field from tribal knowledge into a **live, grounded, self-updating data layer** that feeds discovery, messaging, conversation, and learning.

---

## §C.1 — Layer Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  C6  ARMAMENT         Battlecards · objection handlers · trap-setting  │
├──────────────────────────────────────────────────────────────────────┤
│  C5  WIN/LOSS         Competitive attribution · head-to-head ledger    │
├──────────────────────────────────────────────────────────────────────┤
│  C4  DISPLACEMENT     Vulnerability windows · switch-trigger scoring   │
├──────────────────────────────────────────────────────────────────────┤
│  C3  POSITIONING      Differentiation matrix · axis mapping · claims   │
├──────────────────────────────────────────────────────────────────────┤
│  C2  COMPETITOR MODEL Entity registry · product · pricing · segment    │
├──────────────────────────────────────────────────────────────────────┤
│  C1  MARKET WATCH     Continuous harvest · change detection · dedup    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## §C.2 — Squads

| Squad | Owns | Runtime |
|---|---|---|
| **Watch Squad** | continuous competitor + market harvest; change detection, not re-scraping | `cmi-watch` (Crawl4AI + n8n) |
| **Registry Squad** | canonical competitor entities, products, pricing, ICP overlap, segment strength | `cmi-registry` (Postgres) |
| **Positioning Squad** | maintains the differentiation matrix; maps every claim to a defensible axis | `cmi-position` (CrewAI) |
| **Displacement Squad** | scores vulnerability windows; emits switch triggers into WG2 | `cmi-displace` |
| **Win/Loss Squad** | competitive attribution on every outcome; head-to-head ledger | `cmi-winloss` |
| **Armament Squad** | generates and refreshes battlecards, objection handlers, and trap questions | `cmi-arm` (LiteLLM) |

---

## §C.3 — Market Watch (C1)

Watch surfaces, harvested on independent cadences with **change detection** (hash-diff per surface — the system reacts to *deltas*, never to full re-reads):

| Surface | Signal produced |
|---|---|
| Competitor pricing pages | price rise, tier restructure, packaging change |
| Product/changelog/release notes | feature parity shifts, deprecations |
| Review sites (G2/Capterra-class) | complaint clusters, rating slope, churn language |
| Job boards | strategic direction, team contraction, pivot |
| Funding & M&A feeds | acquisition (→ integration chaos window), raise, distress |
| Status pages & incident feeds | outage frequency, reliability erosion |
| Security/breach disclosures | trust rupture — the strongest displacement trigger |
| Leadership changes | strategy reset, account-team disruption |
| Community & forums | unfiltered switching intent |
| Ad & content footprint | positioning shift, segment retargeting |

> **Sovereignty note:** all harvest runs on the client's Crawl4AI, respecting robots/ToS, with provenance stamped on every datum (§G.5). No competitive-intel SaaS subscription is required or assumed.

---

## §C.4 — Competitor Registry (C2)

Each competitor is a versioned entity:

```
competitor_id · canonical_name · aliases · domains
products[] · pricing_model · price_points · packaging
icp_overlap (segment × size × geo)   → where we actually collide
strength_axes[] · weakness_axes[]     → evidence-backed, each with citations
switching_cost_profile                → contract length, lock-in depth, data portability
head_to_head_record                   → from C5, per segment
last_verified_at · confidence
```

**Tiering:** `T1 Direct` (collide in every deal) · `T2 Adjacent` (collide in some segments) · `T3 Status Quo` (spreadsheets, manual process, in-house build) · `T4 Do Nothing`.

> **Doctrine:** T3/T4 are usually the *real* competitors and are the ones every competitive program forgets. Dominion models them explicitly — "do nothing" gets a battlecard.

---

## §C.5 — Positioning & Differentiation Matrix (C3)

A grid of **evaluation axes × vendors**, where each cell holds a claim, an evidence citation, and a confidence.

| Cell state | Meaning | Message strategy |
|---|---|---|
| **We win, they lose** | defensible advantage | lead with it; set a trap question |
| **Parity** | both adequate | neutralize — never argue parity |
| **We lose** | genuine gap | acknowledge honestly, reframe axis importance |
| **Unknown** | no evidence | **never claim** — Send Gate blocks it |

**Trap questions** are the offensive artifact: questions a prospect can ask *any* vendor, where our answer is strong and the competitor's is structurally weak. Generated per competitor, per axis, and armed into both AI messages and the Cockpit.

> **Grounding rule (hard):** every competitive claim used in outbound must cite a registry datum with `sourced_at`. Unsourced or stale (> freshness window) claims fail §G.3 check #2. **Dominion never lets an AI trash-talk a competitor from memory.**

---

## §C.6 — Displacement Engine (C4) — the offensive core

The highest-converting outbound in B2B is not "we exist" — it is **"the thing you already bought just broke."**

**Displacement Score**

```
DS = (vulnerability_severity × recency_decay)
   × incumbent_fit_gap
   × switching_feasibility
   × our_axis_advantage
```

| Vulnerability event | Severity | Window |
|---|---|---|
| Security breach / data incident | Critical | 0–30 days |
| Acquisition by a larger vendor | High | 30–180 days (integration chaos) |
| Price increase / repackaging | High | at renewal ± 60 days |
| Sustained outage pattern | High | 0–45 days |
| Product deprecation of a used feature | High | 0–90 days |
| Complaint cluster on review sites | Medium | rolling |
| Leadership exodus | Medium | 30–120 days |
| Contract renewal date (inferred) | Medium | −90 days |

When `DS ≥ threshold`, CMI emits `displacement.window.open` into the **WG2 signal ingress** — competitive vulnerability becomes a first-class discovery trigger, ranked alongside funding and hiring signals. In ABM (Module ⑩) it routes to the role that owns the pain: breaches → risk owner, price rises → economic buyer, outages → technical evaluator.

**Ethics gate:** displacement messaging attacks *the situation*, never the vendor. Disparagement is blocked at §G.3 check #4. The move is "here is a way to remove this risk," not "your vendor is bad."

---

## §C.7 — Competitive Conversation Handling (into W5)

CMI extends the W5 classifier with a **competitor-mention detector**:

| Reply pattern | CMI action |
|---|---|
| "We already use **X**" | pull X's battlecard → displacement-aware response → log `competitor.detected` |
| "How do you compare to **X**?" | grounded differentiation, axis-honest, trap question attached |
| "**X** is cheaper" | switching-cost + TCO reframe from registry price points |
| "We're evaluating **X** and **Y**" | multi-vendor bake-off mode → arm champion (Module ⑩) with a scorecard |
| Vendor named but unknown to registry | **create competitor stub, escalate to Cockpit, respond neutrally** — never improvise |

Every competitor mention writes to the account graph as `(:Account)-[:USES]->(:Competitor)`, building — over time — a **live incumbency map of the entire market**. That map is a compounding asset no rented tool gives back to you.

---

## §C.8 — Win/Loss Intelligence (C5)

WL1's outcome ingest gains a competitive dimension. Every terminal outcome captures:

`competitor_present` · `competitor_id` · `outcome` (won / lost-to / lost-to-nothing) · `decisive_axis` · `price_delta` · `evidence` (quotes from the thread, not a dropdown).

**Head-to-head ledger** — win rate vs. each competitor, sliced by segment, size, signal type, and committee shape. This produces the three most valuable sentences a GTM team can own:

1. *"We beat X in sub-200-employee SaaS on deployment speed, 71% of the time."*
2. *"We lose to Y whenever procurement enters before our champion has an executive sponsor."*
3. *"Our real competitor in mid-market is do-nothing, and it beats us on urgency, not features."*

**Feeds WL2-6:** competitor-aware ICP refinement (deprioritize segments we structurally lose), axis reweighting in copy models, and loss-reason separation — *lost to a competitor* vs. *lost to inertia* vs. *never reached the buyer* (Module ⑩). Three different failures, three different fixes; without CMI they are one undifferentiated "lost."

---

## §C.9 — Auto-Battlecards (C6)

Battlecards are **generated artifacts, not documents**. Each is regenerated on every material registry change and version-stamped:

```
BATTLECARD · {competitor} · v{n} · generated {date} · freshness {green|amber|red}
  1  One-line positioning of them (fair, defensible)
  2  Where we win — with evidence citations
  3  Where they win — honestly stated, with our reframe
  4  Their current vulnerabilities (live from C4, with expiry dates)
  5  Trap questions (3–5)
  6  Objection handlers (their strongest 5 attacks on us)
  7  Pricing reality + switching-cost math
  8  Head-to-head record in this segment (live from C5)
  9  Proof assets to attach
```

Surfaced in the Cockpit (Module ⑧) inline in any thread where a competitor is detected, and indexed into **AnythingLLM** so a human can simply ask *"how do we beat X in fintech?"* and get a grounded, cited answer.

**Freshness enforcement:** every card carries a status. Red cards are withheld from AI messaging entirely and flagged to the operator — a stale battlecard is worse than none.

---

## §C.10 — Event Contracts

**Consumes:** `reply.classified` (W5), `meeting.won` / `meeting.lost` (WL1), `account.resolved` / `committee.mapped` (⑩), scheduled watch ticks.

**Emits:**

| Event | Consumer |
|---|---|
| `competitor.change.detected` | registry, positioning, armament |
| `displacement.window.open` | **WG2 signal ingress**, ⑩ play runner |
| `competitor.detected` (in a live thread) | W5, Cockpit, account graph |
| `battlecard.updated` | Cockpit, AnythingLLM index |
| `winloss.attributed` | WL2-6 learning flywheel |
| `positioning.gap.detected` | Cockpit → product/founder feedback |
| `claim.stale` | Send Gate (blocks the claim) |

---

## §C.11 — Roadmap

- **Phase 0 — Registry & watch.** Competitor entities (incl. T3 status-quo, T4 do-nothing) + change-detected harvest on pricing, changelog, reviews. *Exit: every material competitor change is detected within 24h.*
- **Phase 1 — Conversation handling.** Competitor-mention detection in W5 + grounded responses + incumbency mapping into the graph. *Exit: no competitor mention is answered generically.*
- **Phase 2 — Battlecards & Cockpit.** Auto-generated, freshness-stamped cards; AnythingLLM Q&A. *Exit: reps stop maintaining decks.*
- **Phase 3 — Displacement engine.** DS scoring → `displacement.window.open` into WG2, role-routed via ⑩. *Exit: competitive vulnerability is a top-3 source of qualified pipeline.*
- **Phase 4 — Win/loss learning.** Head-to-head ledger → WL2-6 segment and axis reweighting. *Exit: ICP automatically deprioritizes structurally losing segments.*

---

## §C.12 — Elite Differentiators

- **Displacement as a discovery source.** Most systems wait for a prospect to be curious; Dominion detects the moment their current solution becomes a liability and arrives inside the window.
- **Grounded competitive claims or none.** Every comparative statement cites a dated, sourced datum, and stale claims are structurally blocked. The machine is more factually disciplined about competitors than most human reps.
- **Honest-axis positioning.** The matrix records where we *lose* and teaches the system to reframe rather than deny — which is exactly why prospects believe the parts where we win.
- **A live incumbency map of your market.** Every competitor mention ever received compounds into a graph of who uses what — a proprietary dataset that grows only because you own the pipeline.
- **Loss reasons that are actually actionable.** Separating "lost to competitor," "lost to inertia," and "never reached the buyer" repairs the flywheel's most expensive mislabeling.
- **Battlecards that cannot rot.** Regenerated on change, freshness-gated, and withheld when stale — the opposite of the quarterly deck nobody trusts.

---

*CMI v1.0 · Module ⑪ of the Prospect Dominion Elite Edge · feeds WG2 (displacement triggers), W5 (competitive replies), ⑩ (role routing), WL2-6 (win/loss learning) · all claims gated by GOV §G.3 · surfaced in Cockpit ⑧ and AnythingLLM.*
