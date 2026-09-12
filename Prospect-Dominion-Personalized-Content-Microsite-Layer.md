# 🎬 Prospect Dominion — Personalized Content & Microsite Layer

> **Module ⑫ · PCM v1.0 · Elite Edge Layer**
> Every module so far optimizes the **message**. This one optimizes the **destination**. A cold email can carry perhaps 90 words of personalization; a generated microsite can carry an entire tailored argument — the prospect's own signals, their committee's roles, their incumbent's weaknesses, a scoped plan, and a booking CTA — rendered per account, hosted on infrastructure the client owns, and instrumented as the highest-fidelity intent sensor in the whole system.

---

## §P.0 — Why This Module Exists

Dominion's touches currently terminate in one of two places: a reply, or a generic website. Both waste the intelligence upstream.

- **The pitch is compressed into the email.** All the enrichment (W2), psychographics, committee mapping (⑩), and competitive intel (⑪) get squeezed into a subject line and three sentences, then discarded.
- **Click ≠ intent, today.** A click on a generic homepage is nearly signal-free. A 4-minute session on a page built for *your company's specific problem*, shared internally to two colleagues, is the strongest pre-reply buying signal that exists — and Dominion cannot currently observe it.
- **Champions have nothing to forward.** In committee deals (⑩), the champion must sell internally. Forwarding a cold email is embarrassing; forwarding a tailored, credible page is easy. **Forwardability is a conversion mechanic.**
- **Third-party dependency.** Video-personalization and microsite vendors are exactly the rented SaaS the sovereignty thesis rejects — and they pixel-track your prospects on someone else's servers.

PCM makes the destination as personalized as the message, and keeps it entirely inside the client's estate.

---

## §P.1 — Layer Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  P6  SIGNAL LOOP      Engagement telemetry · intent scoring · alerts   │
├──────────────────────────────────────────────────────────────────────┤
│  P5  DELIVERY         Own-domain hosting · privacy-safe tracking · TTL │
├──────────────────────────────────────────────────────────────────────┤
│  P4  MEDIA FORGE      Personalized video · audio · dynamic imagery     │
├──────────────────────────────────────────────────────────────────────┤
│  P3  ASSEMBLY         Block composition · narrative · CTA selection    │
├──────────────────────────────────────────────────────────────────────┤
│  P2  CONTENT MODEL    Block library · proof registry · variant rules   │
├──────────────────────────────────────────────────────────────────────┤
│  P1  BRIEF BUILDER    Pulls account/committee/competitor/signal context│
└──────────────────────────────────────────────────────────────────────┘
```

---

## §P.2 — Squads

| Squad | Owns | Runtime |
|---|---|---|
| **Brief Squad** | assembles the per-account content brief from Postgres, Neo4j, Qdrant, Mem0, CMI registry | `pcm-brief` |
| **Composition Squad** | selects and orders blocks; writes the narrative; picks the CTA | `pcm-compose` (CrewAI + LiteLLM) |
| **Media Squad** | renders personalized video, voice-over, and dynamic imagery | `pcm-media` (ffmpeg + TTS/avatar + `magick`) |
| **Publish Squad** | builds static pages, hosts on own domain, manages TTL and revocation | `pcm-publish` (Garage + edge server) |
| **Telemetry Squad** | first-party engagement events, share detection, intent scoring | `pcm-signal` |
| **Governance Bridge** | routes every generated asset through the Send Gate before it becomes reachable | `governance-svc` (§G.3) |

---

## §P.3 — The Content Brief (P1)

Nothing is generated from a prompt alone. Each microsite starts from a **structured, provenance-stamped brief**:

| Source | Contributes |
|---|---|
| **W2 enrichment** | firmographics, stack, headcount shape, footprint |
| **WG2 signal** | the *why now* trigger, with date and citation |
| **⑩ committee map** | which roles will read this; who the champion is |
| **⑪ competitor registry** | incumbent (if known), relevant axes, live vulnerabilities |
| **Psychographics (L-GEN)** | tone target, risk posture, decision style |
| **Mem0 thread memory** | anything already said — the page must never contradict the emails |
| **Proof registry** | approved case studies, metrics, logos matched by segment |

> **Hard rule:** every factual statement on the page must resolve to a brief datum with provenance. The page is subject to the same grounding standard as an email (§G.3 check #1). No invented statistics, no imagined pain, no fabricated customer names.

---

## §P.4 — Block Library (P2) & Assembly (P3)

Pages are **composed from approved blocks**, never free-written end to end. This is what makes generation safe at scale.

| Block | Personalization axis | Grounding source |
|---|---|---|
| `hero` | company name + the specific trigger event | WG2 signal |
| `mirror` | "here's what we observed about your situation" | W2 + signal, cited |
| `thesis` | the account narrative (shared with ⑩ — one thesis, many surfaces) | ⑩ account thesis |
| `role_lens` | a section per committee role present | ⑩ committee map |
| `proof` | case study matched on segment + size + trigger type | proof registry |
| `comparison` | axis-honest differentiation vs. detected incumbent | ⑪ matrix |
| `plan` | scoped 30/60/90 outline for *their* situation | offer catalog |
| `economics` | ROI framing using their own scale inputs | W2 firmographics |
| `objection` | pre-answers the top objection for their profile | ⑪ handlers |
| `media` | personalized video / voice note | P4 |
| `cta` | book, reply, or forward-to-colleague | WV booking |
| `provenance` | "how we found you" + data rights + opt-out | §G.5 / §G.1 |

**Assembly rules:** block count scales with deal size (3 blocks for SMB, 9+ for enterprise ABM); `role_lens` only appears when ≥2 roles are mapped; `comparison` only appears when an incumbent is *known* and its card is fresh-green (⑪ §C.9); `provenance` is **mandatory and non-removable** on every page.

> The `provenance` block is a differentiator, not a compliance tax. Telling a prospect exactly how you found them — in plain language, with an opt-out — converts better than pretending it was serendipity.

---

## §P.5 — Media Forge (P4)

Fully self-hosted, no personalization SaaS:

| Asset | Method | Personalization |
|---|---|---|
| **Personalized video** | pre-recorded founder base clips + a generated intro segment; concatenated via `ffmpeg` | name, company, trigger, incumbent |
| **Dynamic thumbnail** | `magick` composite — a real screenshot of *their* site/careers page behind a play button | visual proof it is not a blast |
| **Voice note** | self-hosted TTS (or cloned founder voice, with consent) | 20–30s, trigger-specific |
| **Dynamic imagery** | their logo in a workflow diagram; their stack in an architecture sketch | stack from W2 |
| **Scoped one-pager PDF** | rendered from the same brief | full page content, offline-shareable |

**Cost discipline:** media renders only when `lead_score ≥ threshold` or the account is in an ⑩ play at `S4+`. Everything else gets a text microsite. Rendering a video for a cold, unqualified lead is exactly the kind of expensive theatre this system exists to avoid.

**Consent discipline:** voice cloning requires written consent from the voice owner, recorded in the audit ledger. No synthetic likeness of anyone who has not signed off.

---

## §P.6 — Delivery & Privacy (P5)

| Control | Implementation |
|---|---|
| **Hosting** | static bundle in **Garage** (S3), served from a client-owned subdomain (`go.clientdomain.com`) |
| **URL** | unguessable token; **never** encodes name or email in the path |
| **Isolation** | one page per account (or per role); no cross-account enumeration possible |
| **TTL** | pages expire (default 90 days) and auto-revoke; expired pages return a neutral, non-leaky landing |
| **Tracking** | **first-party only** — no third-party pixels, no ad networks, no analytics SaaS |
| **Data minimization** | telemetry stores engagement events, never keystrokes, never session recordings |
| **Deletion** | DSAR erasure (§G.5) cascades to the page bundle, media assets, and all telemetry |
| **Robots** | `noindex`, excluded from sitemaps — a prospect's page must never surface in search |
| **Kill switch** | `killswitch-svc` can revoke every live page instantly (§G.7) |

> **Sovereignty check:** the prospect's browsing behavior is observed by the client's own server and nobody else. Compared to the standard practice of routing prospect behavior through three ad-tech vendors, this is a genuine trust argument you can make out loud on the page itself.

---

## §P.7 — Engagement Telemetry → Intent (P6)

This is the module's strategic payload. Microsite engagement is a **far higher-resolution intent signal** than email opens (which are now largely noise from privacy proxies).

| Event | Intent weight | Interpretation |
|---|---|---|
| `page.viewed` | low | curiosity |
| `dwell ≥ 60s` | medium | genuine reading |
| `scroll_depth ≥ 75%` | medium | consumed the argument |
| `block.engaged` (which sections) | **high** | *reveals what they actually care about* |
| `media.watched ≥ 50%` | high | strong attention |
| `asset.downloaded` | high | building an internal case |
| `page.revisited` | high | deliberation |
| `new_visitor_same_page` | **critical** | **it was forwarded internally — the committee is engaged** |
| `cta.clicked` | critical | ready |

**Composite Content Intent Score (CIS)** feeds directly into:
- **W2/scoring** — CIS raises the lead score; a high-CIS silent prospect is *not* cold and should never be treated as such.
- **WO1 next-touch** — the follow-up references the block they lingered on. This is the sharpest personalization in the entire system: *responding to what they read, not what you sent.*
- **⑩ play runner** — a forward event fires `champion.identified` and advances the account state.
- **Cockpit ⑧** — a real-time alert: *"3 people from Acme are reading the page right now."* The single most actionable notification a rep can receive.

---

## §P.8 — Event Contracts

**Consumes:** `lead.scored` (W2), `touch.sent` (WO1), `account.resolved` / `committee.mapped` / `play.state.changed` (⑩), `competitor.detected` / `battlecard.updated` (⑪), `reply.classified` (W5).

**Emits:**

| Event | Payload | Consumer |
|---|---|---|
| `content.brief.built` | brief id, sources, provenance | compose |
| `microsite.published` | url token, blocks, TTL, account_id | WO1 (injects link into the touch) |
| `media.rendered` | asset ids, type, cost | publish, audit |
| `content.engaged` | event type, block, dwell, visitor hash | scoring, ⑩, Cockpit |
| `content.forwarded` | new-visitor evidence | **⑩ `champion.identified`**, Cockpit alert |
| `content.intent.scored` | CIS, contributing events | W2 scoring, WO1 |
| `microsite.expired` / `revoked` | url token, reason | audit |

---

## §P.9 — Governance Seam

- Every assembled page passes the **Send Gate (§G.3)** *before publication*: grounding, claims, brand safety, and legal blocks are checked exactly as for an email. A page is an outbound artifact.
- **Fail-closed:** if the gate is unreachable, the page is not published; the touch falls back to a plain message with no link.
- Comparison blocks require a **fresh-green battlecard** (⑪ §C.9); amber/red suppresses the block automatically.
- Every publication, render, view, and revocation writes to the **audit ledger (§G.5)** — you can reconstruct exactly what any prospect was shown, on any date.
- **Autonomy Dial (⑧):** at A0/A1 a human previews and approves pages before publish; A2 auto-publishes within pre-approved block templates only.

---

## §P.10 — Roadmap

- **Phase 0 — Text microsites.** Brief builder + 5 core blocks + Garage hosting on own subdomain + first-party telemetry. *Exit: every high-score touch links to a grounded, personalized page.*
- **Phase 1 — Intent loop.** CIS scoring into W2; block-level engagement into WO1 follow-ups; Cockpit live-reader alerts. *Exit: follow-ups reference what the prospect actually read.*
- **Phase 2 — Committee pages.** `role_lens` + `comparison` blocks; forward detection → `champion.identified` into ⑩. *Exit: internal forwarding is detected and acted on.*
- **Phase 3 — Media forge.** Personalized video, dynamic thumbnails, voice notes, scoped PDFs — gated by score and play state. *Exit: media renders only where economically justified.*
- **Phase 4 — Learning.** Block-level and page-variant performance into WL2-6; the assembler learns which blocks convert by segment and role. *Exit: page composition self-optimizes under the §G.4 promotion gate.*

---

## §P.11 — Elite Differentiators

- **The destination is as personalized as the message.** Competitors personalize 90 words; Dominion personalizes the entire argument the prospect walks into.
- **The highest-fidelity intent sensor you can own.** Block-level dwell tells you *which part of your pitch landed* — a resolution no open-rate or reply-rate metric can approach.
- **Forward detection = champion detection.** When a page is shared internally, the system learns the committee is live before anyone has replied. That is a competitive advantage measured in weeks.
- **Grounded pages, block-composed.** Generation is constrained to an approved, cited block library and gated before publication — scale without hallucination.
- **Radical provenance as a conversion asset.** Telling prospects exactly how you found them, with a one-click opt-out, builds the credibility that the rest of the page then spends.
- **No third party watches your prospects.** First-party hosting, first-party telemetry, own domain, TTL, and instant revocation — self-hosted personalization that replaces an entire category of rented SaaS.
- **Economically disciplined.** Expensive media renders only for accounts that earned it; everyone else gets a page that still beats a generic homepage by a wide margin.

---

*PCM v1.0 · Module ⑫ of the Prospect Dominion Elite Edge · consumes W2/WO1/W5/⑩/⑪ · feeds scoring, WO1 follow-ups, ⑩ champion detection, WL2-6 learning · gated by GOV §G.3/§G.5/§G.7 · surfaced in Cockpit ⑧.*
