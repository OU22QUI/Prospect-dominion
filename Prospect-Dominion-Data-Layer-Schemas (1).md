# 🗄️ Prospect Dominion — Data Layer Schemas

> **Module DATA v1.0** — Sovereign Data Layer (Postgres · Neo4j · Qdrant · Mem0)
> **Baseline:** ADD-GAP §14 (Platform/Infra Sovereignty) · Blueprint v1.1 · L-SEND · L-CONV · L-LEARN
> **Purpose:** The concrete, runnable schema that replaces `aethonex.db` (SQLite) and becomes the single source of truth every layer (L0–L7) and every product (P1–P10) reads and writes.
> **House style:** layer stack · squads · §-numbering · event-driven · workflows · roadmap · elite differentiators.

---

## §0. Design Principles

1. **People and accounts are separate first-class entities.** A person can move companies; an account has many people. The old lead-centric SQLite table conflates them — this fixes it.
2. **One thread per prospect, every channel.** `thread` is the spine across L-OMNI / L-CONV / L-LEARN / L-SEND. Every touch, reply, and call hangs off it.
3. **Append-only outcomes.** Nothing downstream of "sent" is ever overwritten — sends, events, and outcomes are immutable rows so the learning loop (L-LEARN) has clean labels.
4. **Suppression is a hard gate, not a flag.** A dedicated table checked before *every* send (ADD-GAP §9).
5. **Idempotency everywhere.** Every externally-triggered write carries an idempotency key so the event bus can retry safely.
6. **Three stores, clear roles:** Postgres = relational truth · Neo4j = relationships (committee + warm-intro graph) · Qdrant = vector memory · Mem0 = agent working memory. Postgres holds the canonical IDs; the others reference them.

---

## §1. Store Topology

| Store | Role | Canonical for |
|---|---|---|
| **Postgres** | Relational core | people, accounts, threads, touches, sends, events, outcomes, suppression, fleet, campaigns |
| **Neo4j** | Relationship graph | buying committee, warm-intro paths, account↔person↔employee edges |
| **Qdrant** | Vector memory | message embeddings, enrichment-doc embeddings, RAG retrieval |
| **Mem0** | Agent memory | per-thread agent working memory / conversation state |

> **Foreign-key discipline:** Neo4j nodes and Qdrant points store the Postgres UUID (`pg_id`) as a property/payload field. Postgres never stores graph or vector state — it stores the IDs those systems key on.

---

## §2. Postgres — Core Relational Schema

Postgres 16+. Uses `uuid`, `jsonb`, `citext`, `pg_trgm`. All timestamps `timestamptz` in UTC.

### §2.1 — Extensions & Enums

```sql
create extension if not exists "uuid-ossp";
create extension if not exists "citext";
create extension if not exists "pg_trgm";

create type tier_t          as enum ('S','A','B','C','D');
create type verify_status_t as enum ('valid','risky','catch_all','invalid','unknown');
create type channel_t       as enum ('email','linkedin','voice','sms');
create type touch_dir_t     as enum ('outbound','inbound');
create type send_status_t   as enum ('queued','sent','delivered','bounced','complained','failed','suppressed');
create type reply_intent_t  as enum ('interested','objection','question','ooo','unsubscribe','referral','not_interested','auto','other');
create type opp_stage_t     as enum ('new','engaged','meeting_booked','opportunity','won','lost','disqualified');
create type suppress_reason_t as enum ('unsubscribe','complaint','hard_bounce','manual','global_dnc','role_account','competitor');
create type mailbox_health_t as enum ('warming','healthy','degraded','quarantined','retired');
create type consent_basis_t  as enum ('legitimate_interest','consent','contract','none');
```

### §2.2 — Accounts (companies)

```sql
create table account (
  id              uuid primary key default uuid_generate_v4(),
  domain          citext unique not null,
  legal_name      text,
  display_name    text,
  country         text,
  region          text,
  employee_band   text,
  revenue_band    text,
  industry        text,
  business_model  text,                         -- from OSINT layer 2
  icp_score       numeric(5,2),                 -- L4
  icp_tier        tier_t,
  enrichment      jsonb not null default '{}',  -- 10-layer OSINT blob
  enriched_at     timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index on account using gin (enrichment jsonb_path_ops);
create index on account (icp_tier, icp_score desc);
```

### §2.3 — People (contacts)

```sql
create table person (
  id              uuid primary key default uuid_generate_v4(),
  account_id      uuid references account(id) on delete set null,
  full_name       text,
  first_name      text,
  last_name       text,
  title           text,
  seniority       text,
  role_function   text,                         -- e.g. marketing, eng, exec
  linkedin_url    citext,
  location        text,
  is_role_account boolean not null default false,
  psychographics  jsonb not null default '{}',  -- Blueprint v1.1
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (account_id, linkedin_url)
);
create index on person (account_id);
create index on person using gin (full_name gin_trgm_ops);
```

### §2.4 — Email addresses (verification lives here, not on person)

```sql
create table email_address (
  id              uuid primary key default uuid_generate_v4(),
  person_id       uuid references person(id) on delete cascade,
  address         citext not null unique,
  pattern         text,                          -- first.last@, first@ ...
  is_primary      boolean not null default false,
  verify_status   verify_status_t not null default 'unknown',
  verify_score    numeric(4,3),                  -- confidence 0..1 (ADD-GAP §2)
  verified_at     timestamptz,
  reverify_after  timestamptz,                   -- TTL cache
  created_at      timestamptz not null default now()
);
create index on email_address (person_id);
create index on email_address (verify_status, reverify_after);
```

### §2.5 — Threads (the spine — one per prospect, all channels)

```sql
create table thread (
  id              uuid primary key default uuid_generate_v4(),
  person_id       uuid not null references person(id) on delete cascade,
  account_id      uuid references account(id) on delete set null,
  campaign_id     uuid references campaign(id) on delete set null,
  opp_stage       opp_stage_t not null default 'new',
  consent_basis   consent_basis_t not null default 'none',
  next_action_at  timestamptz,
  last_touch_at   timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (person_id, campaign_id)                -- one thread per person per campaign
);
create index on thread (opp_stage, next_action_at);
create index on thread (account_id);
```

### §2.6 — Campaigns

```sql
create table campaign (
  id            uuid primary key default uuid_generate_v4(),
  name          text not null,
  niche         text,
  channel_mix   channel_t[] not null default '{email}',
  status        text not null default 'draft',
  config        jsonb not null default '{}',     -- cadence, angles, A/B variants
  created_at    timestamptz not null default now()
);
```

### §2.7 — Touches (every outbound/inbound interaction, any channel)

```sql
create table touch (
  id            uuid primary key default uuid_generate_v4(),
  thread_id     uuid not null references thread(id) on delete cascade,
  channel       channel_t not null,
  direction     touch_dir_t not null,
  step_no       int,                             -- position in cadence
  variant       text,                            -- A/B/n label (L7)
  subject       text,
  body          text,
  grounding     jsonb not null default '{}',     -- FPG evidence per claim
  occurred_at   timestamptz not null default now(),
  created_at    timestamptz not null default now()
);
create index on touch (thread_id, occurred_at);
create index on touch (channel, direction);
```

### §2.8 — Sends (email dispatch state — the L-SEND ledger)

```sql
create table send (
  id             uuid primary key default uuid_generate_v4(),
  touch_id       uuid not null references touch(id) on delete cascade,
  mailbox_id     uuid not null references mailbox(id),
  message_id     text unique,                    -- RFC Message-ID
  status         send_status_t not null default 'queued',
  idempotency_key text unique not null,
  queued_at      timestamptz not null default now(),
  sent_at        timestamptz,
  delivered_at   timestamptz,
  error          text
);
create index on send (status, queued_at);
create index on send (mailbox_id, sent_at);
```

### §2.9 — Events (append-only telemetry: opens, bounces, complaints, FBL)

```sql
create table event (
  id             bigint generated always as identity primary key,
  send_id        uuid references send(id) on delete cascade,
  thread_id      uuid references thread(id) on delete cascade,
  type           text not null,                  -- delivered|open|click|bounce|complaint|reply|fbl
  subtype        text,                           -- hard|soft, etc.
  payload        jsonb not null default '{}',
  occurred_at    timestamptz not null default now()
);
create index on event (type, occurred_at);
create index on event (thread_id, occurred_at);
create index on event (send_id);
```

### §2.10 — Replies (classified inbound — L-CONV / ADD-GAP §4)

```sql
create table reply (
  id             uuid primary key default uuid_generate_v4(),
  thread_id      uuid not null references thread(id) on delete cascade,
  touch_id       uuid references touch(id),
  intent         reply_intent_t not null default 'other',
  intent_score   numeric(4,3),
  sentiment      numeric(4,3),
  raw_body       text,
  routed_to      text,                           -- rep/queue/auto
  handled_at     timestamptz,
  created_at     timestamptz not null default now()
);
create index on reply (intent, created_at);
create index on reply (thread_id);
```

### §2.11 — Outcomes (append-only labels for the learning loop — L-LEARN §5)

```sql
create table outcome (
  id             uuid primary key default uuid_generate_v4(),
  thread_id      uuid not null references thread(id) on delete cascade,
  account_id     uuid references account(id),
  stage_from     opp_stage_t,
  stage_to       opp_stage_t not null,
  reason         text,
  value_amount   numeric(14,2),                  -- deal value if won
  attributed_signal text,                        -- originating signal (attribution)
  occurred_at    timestamptz not null default now()
);
create index on outcome (stage_to, occurred_at);
create index on outcome (account_id);
```

### §2.12 — Suppression (hard gate — checked before EVERY send, ADD-GAP §9)

```sql
create table suppression (
  id             uuid primary key default uuid_generate_v4(),
  address        citext,
  domain         citext,
  reason         suppress_reason_t not null,
  scope          text not null default 'global', -- global|campaign
  campaign_id    uuid references campaign(id),
  created_at     timestamptz not null default now(),
  constraint suppress_target check (address is not null or domain is not null)
);
create unique index on suppression (address) where address is not null and scope='global';
create index on suppression (domain);
```

> **Enforcement:** the send worker runs `select 1 from suppression where (address = $1 or domain = $2)` before enqueuing. A hit sets `send.status='suppressed'` and emits an audit event. No suppression check → no send.

### §2.13 — Sending fleet (L-SEND: domains, mailboxes, reputation)

```sql
create table sending_domain (
  id             uuid primary key default uuid_generate_v4(),
  domain         citext unique not null,
  spf_ok         boolean default false,
  dkim_ok        boolean default false,
  dmarc_policy   text,                           -- none|quarantine|reject
  mta_sts_ok     boolean default false,
  ip_pool        text,
  warmup_started timestamptz,
  reputation     numeric(4,3),                   -- rolling health 0..1
  created_at     timestamptz not null default now()
);

create table mailbox (
  id             uuid primary key default uuid_generate_v4(),
  domain_id      uuid not null references sending_domain(id) on delete cascade,
  address        citext unique not null,
  daily_cap      int not null default 20,
  sent_today     int not null default 0,
  health         mailbox_health_t not null default 'warming',
  reputation     numeric(4,3),
  last_send_at   timestamptz,
  created_at     timestamptz not null default now()
);
create index on mailbox (health, reputation desc);
```

> **Reputation router (ADD-GAP §1):** `select ... from mailbox where health='healthy' and sent_today < daily_cap order by reputation desc limit 1` — picks the healthiest available mailbox per send.

### §2.14 — Audit log (governance / kill switch — module ⑦)

```sql
create table audit_log (
  id             bigint generated always as identity primary key,
  actor          text not null,                  -- agent/human/system
  action         text not null,
  entity_type    text,
  entity_id      uuid,
  detail         jsonb not null default '{}',
  occurred_at    timestamptz not null default now()
);
create index on audit_log (entity_type, entity_id);
create index on audit_log (action, occurred_at);
```

---

## §3. Neo4j — Relationship Graph

Powers the buying committee (module ⑩) and warm-intro paths (module ⑬). Nodes carry the Postgres UUID as `pg_id`.

### §3.1 — Node labels

```
(:Account   {pg_id, domain, name, tier})
(:Person    {pg_id, name, title, seniority, role_function})
(:Employee  {pg_id, name})            // your team / network (the 1,082 connections)
(:Signal    {type, source, occurred_at})
```

### §3.2 — Relationships

```
(:Person)-[:WORKS_AT {since}]->(:Account)
(:Person)-[:REPORTS_TO]->(:Person)
(:Person)-[:ROLE {committee_role}]->(:Account)   // champion|blocker|economic_buyer|user
(:Employee)-[:KNOWS {strength, source}]->(:Person)  // warm-intro edge
(:Account)-[:HAS_SIGNAL]->(:Signal)
(:Account)-[:COMPETES_WITH]->(:Account)
```

### §3.3 — Signature queries

```cypher
// Warm-intro path into a cold account (module ⑬)
MATCH (e:Employee)-[k:KNOWS]->(p:Person)-[:WORKS_AT]->(a:Account {domain:$domain})
RETURN e.name, p.name, p.title, k.strength
ORDER BY k.strength DESC;

// Buying-committee coverage for an account (module ⑩)
MATCH (p:Person)-[r:ROLE]->(a:Account {domain:$domain})
RETURN r.committee_role, collect(p.name);
```

---

## §4. Qdrant — Vector Memory

| Collection | Vector of | Payload (references Postgres) | Used by |
|---|---|---|---|
| `messages` | touch/reply text embedding | `thread_id`, `touch_id`, `channel`, `variant` | reply classification, RAG cockpit |
| `enrichment_docs` | OSINT/source-doc chunks | `account_id`, `source`, `url` | personalization grounding (FPG) |
| `personas` | ICP centroid vectors | `tier`, `niche` | ICP-diff scoring (L-LEARN §5) |

> **ICP centroid (L-LEARN):** closed-won accounts' enrichment vectors are averaged into a centroid stored in `personas`; a new account's `icp_score` is a function of its cosine distance to the centroid — this is the "learns from closed-won" mechanic.

---

## §5. Mem0 — Agent Working Memory

- Keyed by `thread_id`; holds per-prospect conversational state and agent scratchpad across turns and channels.
- Canonical facts always resolve back to Postgres; Mem0 holds *derived, mutable* working state only, so it can be rebuilt from the relational + vector stores if lost.

---

## §6. Migration — `aethonex.db` (SQLite) → Postgres

**Mapping from the existing 10-layer system:**

| SQLite (current) | Postgres (target) | Notes |
|---|---|---|
| `leads` (3,018) | split → `account` + `person` + `email_address` | de-conflate; dedupe people across niches |
| enriched domains (1,448) | `account.enrichment` (jsonb) + `enriched_at` | one 10-layer blob per account |
| LinkedIn prospects (1,082) | `person` + `email_address` | tiers → `person`/`account` tier fields |
| tier labels (52 S / 1,030 A) | `account.icp_tier` / `thread` | preserve during import |
| send history (single mailbox) | `send` + `mailbox` (seed the fleet) | backfill `founder@` as mailbox #1 |

**Procedure (idempotent, resumable — run as event-bus jobs):**
1. Stand up Postgres schema (§2); create extensions/enums first.
2. Export SQLite tables to CSV/JSONL.
3. **Load accounts** (dedupe on `domain`) → **load people** (dedupe on `linkedin_url` within account) → **load emails** (carry `verify_status`, default `unknown`, set `reverify_after=now()`).
4. Create one `thread` per person for the active campaign; set `opp_stage` from any known state.
5. Seed `sending_domain` + `mailbox` with the existing mailbox as health `healthy`.
6. **Seed suppression** from any known unsubscribes/bounces *before* any new send (§2.12 gate).
7. Load enrichment blobs → embed into Qdrant `enrichment_docs`.
8. Build Neo4j: `Account`, `Person`, `WORKS_AT`; import the 1,082 connections as `Employee`-`KNOWS`-`Person` edges (module ⑬ warm-graph seed).
9. Reconcile counts (accounts / people / emails) against source; log to `audit_log`.

---

## §7. Roadmap (data layer, aligned to ADD-GAP §16)

**Phase 1** — Stand up Postgres §2.1–§2.12; migrate leads; **seed suppression before any send**; seed fleet.
**Phase 2** — Add `event`/`reply`/`outcome` pipelines on the event bus; start capturing outcomes (labels are perishable).
**Phase 3** — Populate Qdrant collections + Neo4j graph; wire warm-intro + committee queries.
**Phase 4** — Centroid/ICP-diff scoring live from `personas`; drift monitoring reads `outcome`.

---

## §8. Elite Differentiators

1. **People ≠ accounts ≠ emails** — proper normalization enables cross-campaign person-dedupe the SQLite prototype can't do.
2. **One thread, every channel** — the `thread` spine makes coordinated ABM structurally native, not bolted on.
3. **Append-only truth** — immutable `send`/`event`/`outcome` gives the learning loop clean, trustworthy labels.
4. **Suppression as a query, not a hope** — a hard DB gate before every send makes compliance mechanical.
5. **Three stores, one ID space** — Postgres UUIDs key Neo4j and Qdrant, so the graph and vectors never drift from truth.
6. **Rebuildable memory** — Mem0/Qdrant are derivable from Postgres, so working state loss is never data loss.

---

### Summary — the one-line schema

> Replace a laptop-bound `aethonex.db` with a normalized, append-only, three-store data layer where **people, accounts, and threads are first-class, suppression is a hard gate, and every store keys off one Postgres ID** — the foundation the whole sovereign machine stands on.
