# 🔄 Prospect Dominion — WL2–WL6 Learning Flywheel Workflow

> **Doc code:** `FLOW-WL2-6 v1.0` · **Type:** Executable n8n workflow set (importable JSON, scheduled + gated)
> **Squad:** Learning Crew (L-LEARN) — Attributor · Model Trainer · Evaluator · Promoter · Drift Sentinel
> **Consumes:** `outcome.logged` (from `FLOW-WL1`) + the append-only Postgres `outcome_log`
> **Emits:** `attribution.updated` · `model.challenger_ready` · `model.promoted` · `icp.diff_proposed` · `drift.alert`
> **Companion to:** `FLOW-WL1` (its intake) · L-LEARN §L.5, §L.6, §L.7, §L.9 · Rep Cockpit (⑧, approval surface)

---

## §WL2-6.0 — Why this workflow set exists

`FLOW-WL1` harvests every outcome into an immutable `outcome_log`. That is memory, not learning. **This set is the learning.** It is the scheduled, off-the-hot-path flywheel that turns labeled outcomes into *proposed* model and asset updates, proves them safe in shadow, gates the high-impact ones behind a human, and deploys the winners back into every consuming module — versioned and rollback-ready.

The prime directive of the whole loop: **the system that closed a deal this week is measurably better at finding the next one — without silent drift and without a redeploy.**

Five stages, five schedules, one flywheel:

| Stage | Workflow | Cadence | One-line job |
|---|---|---|---|
| **Attribute** | WL2 · Attribution Batch | nightly | Multi-touch credit + cohort tagging + Source Genome update |
| **Retrain** | WL3 · Retrain Cycle | weekly / threshold | Run the four retrainers → produce challengers |
| **Prove** | WL4 · Eval & Shadow | on challenger-ready | Backtest + champion/challenger shadow + significance/poisoning gates |
| **Promote** | WL5 · Promotion & Approval | on eval-pass | Explainable-delta packet → Cockpit approval → versioned deploy |
| **Watch** | WL6 · Drift Watch | continuous | Alert on accuracy decay, persona drift, reply-rate erosion, calibration slip |

> **Non-negotiable:** **Attribution precedes training — always.** Correlation-only learning teaches the wrong lessons. WL2 exploits the controlled variation the L-OMNI bandit and copy experiments already produce, so WL3 trains on *causal* lift, not vanity correlation.

---

## §WL2-6.1 — Layer stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  TRIGGER    cron (WL2 nightly · WL3 weekly/threshold) + event          │
│             (WL4 on challenger_ready · WL5 on eval_pass) + WL6 stream  │
├──────────────────────────────────────────────────────────────────────┤
│  WL2 ATTRIBUTE  outcome_log → multi-touch credit → cohort tags →       │
│                 Source Genome (surface→payer) → attribution.updated    │
├──────────────────────────────────────────────────────────────────────┤
│  WL3 RETRAIN    four retrainers on attributed data → challengers       │
│                 (scoring · ICP-diff · persona · copy/channel)          │
├──────────────────────────────────────────────────────────────────────┤
│  WL4 EVAL       offline backtest vs. champion → shadow scoring on live │
│                 traffic → significance + data-poisoning gates          │
├──────────────────────────────────────────────────────────────────────┤
│  WL5 PROMOTE    explainable-delta packet → Cockpit approval (high-     │
│                 impact) / auto (low-risk) → versioned deploy + writeback│
├──────────────────────────────────────────────────────────────────────┤
│  WL6 WATCH      continuous drift/decay monitors → drift.alert          │
├──────────────────────────────────────────────────────────────────────┤
│  RESILIENCE     idempotent batches · reproducible runs (seed+data ver) │
│                 · rollback pointer · Langfuse trace on every stage      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## §WL2-6.2 — Squad & tool bindings

| Role | Agent / Node | Tools |
|---|---|---|
| **Attributor** | WL2 batch | Postgres `outcome_log`, Neo4j (committee/touch graph), Qdrant (message embeddings), attribution models |
| **Model Trainer** | WL3 retrainers ×4 | MLOps pipeline, LiteLLM, local fine-tuning, Postgres feature store |
| **Evaluator** | WL4 harness | Eval harness, held-out set, Langfuse, shadow router |
| **Promoter** | WL5 gate | Model registry (versioned), Rep Cockpit approval API, config/ICP-as-Code store |
| **Drift Sentinel** | WL6 monitor | Metrics store, Langfuse, alerting (Cockpit + email) |

---

## §WL2-6.3 — WL2 · Attribution Batch (nightly)

**Trigger:** cron `0 2 * * *` (nightly, low-traffic window) + a `outcome.logged` counter that can pull the run forward when volume spikes.

**Flow:**
1. **Pull window** — new `outcome_log` rows since `last_attributed_at` (watermark in `learning_state`).
2. **Assign multi-touch credit** — walk each `thread_id`'s touch chain (WO1 sends, W5 replies, WV bookings) and apply the attribution model; where the L-OMNI bandit / copy experiments produced controlled variation, estimate **causal lift** rather than correlation.
3. **Tag cohorts** — stamp each attributed outcome with ICP-segment · persona · source-surface · channel · vertical · variant.
4. **Update Source Genome** — increment surface→*payer* stats (not just surface→reply): which discovery surfaces yield closed-won, at what CAC, at what cycle length. Write back to L-GEN's genome table.
5. **Emit** `attribution.updated` + advance watermark.

**Output tables:** `attribution_credit`, `source_genome`, `cohort_stats`.

> **Elite tap:** the Source Genome update is L-GEN's most important closed loop — discovery stops optimizing for *replies* and starts optimizing for *revenue*.

---

## §WL2-6.4 — WL3 · Retrain Cycle (weekly / threshold)

**Trigger:** cron `0 3 * * 1` (weekly) **OR** `outcome_volume_since_last_retrain >= N` (threshold), whichever first. Never per-event — learning stays off the hot path.

**The four retrainers (each produces a *challenger*, never a live swap):**

| Retrainer | Trains on | Produces | Guardrail |
|---|---|---|---|
| **Predictive Scoring** | `predicted-score → actual-outcome` pairs | New scoring model challenger | Preserve SHAP explainability; target 78–88% band + better calibration |
| **ICP-Diff** | closed-won vs. closed-lost by trait | **PR-style diff** to ICP-as-Code | Never auto-applies — always human PR review |
| **Persona / Psychographic** | response by inferred decision-style | Re-clustered segment map | Flags drift; keeps signal→persona→tone mapping auditable |
| **Copy / Channel** | hook/angle/length/channel/send-time wins per persona×segment | Hardened "playbook" promotions + retirements | Guards against message fatigue (retire decayed patterns) |

**Flow:** load attributed data → run four retrainers in parallel (fan-out) → register each challenger in the model registry with `{data_version, seed, feature_set}` for reproducibility → emit `model.challenger_ready` per model.

---

## §WL2-6.5 — WL4 · Eval & Shadow (on challenger-ready)

**Trigger:** `model.challenger_ready`.

**Gates, in order — a challenger must clear all to proceed:**
1. **Offline backtest.** Score challenger against a held-out set of *recent* outcomes. Must beat the incumbent champion on the target metric (win-rate-per-lead / calibration / reply-quality as applicable).
2. **Champion/Challenger shadow.** Challenger scores live traffic **in parallel, without acting**, until it accumulates enough real decisions to prove out.
3. **Statistical significance.** Require the lift to be significant, not noise (min sample + confidence threshold).
4. **Data-poisoning / anomaly check.** Reject if the training set shows manipulation, a single-cohort dominance skew, or label anomalies.

Pass → emit `model.eval_passed` with the delta packet. Fail → archive challenger with reason; alert WL6.

> **This single stage prevents most self-improvement disasters:** nothing acts on production traffic until it has proven out in shadow.

---

## §WL2-6.6 — WL5 · Promotion & Approval (on eval-pass)

**Trigger:** `model.eval_passed`.

**Routing by impact:**

| Change class | Path | Example |
|---|---|---|
| **High-impact** | **Human-gated** — explainable-delta packet → Rep Cockpit → one-click approve/reject | ICP diffs, scoring-model swaps, persona remap |
| **Low-risk** | **Auto-promote** | Bandit weight nudges, send-time tuning |

**Flow:**
1. Build **explainable-delta packet** — what changes, expected lift, feature attributions, affected cohorts, rollback plan.
2. High-impact → post to Cockpit approval queue; block until decision. Low-risk → skip to deploy.
3. On approval → **versioned deploy**: bump model/ICP-as-Code version, write back to *all* consuming modules (v1.1 [6] scoring, L-GEN ICP, [5] personas, [7] copy, L-OMNI bandit) — **no redeploy of the app; config/version bump only**.
4. Keep the previous version pinned as **rollback pointer**.
5. Emit `model.promoted` (→ WL6 begins watching the new champion) and log the approval to the audit trail.

> **A2 self-directing autonomy realized:** an approved ICP diff shifts all discovery behavior via a version bump — the machine redirects its own targeting, with a human on the high-impact switch.

---

## §WL2-6.7 — WL6 · Drift Watch (continuous)

**Trigger:** stream + cron `*/15 * * * *` rollups.

**Monitors & alerts (`drift.alert` → Cockpit + email):**
- **Accuracy decay** — live scoring accuracy slips below the 78–88% band.
- **Calibration slip** — predicted vs. actual probability diverges.
- **Persona drift** — a segment's behavior shifts from its cluster centroid.
- **Reply-rate erosion / message fatigue** — a promoted copy pattern's reply rate decays past threshold → auto-flag for retirement in the next WL3.
- **North-star** — is **win-rate-per-lead trending up cycle over cycle?** Surfaced on the L-LEARN dashboard.

Drift on a live champion can **auto-trigger a WL3 retrain** ahead of schedule.

---

## §WL2-6.8 — Resilience & reproducibility

- **Idempotent batches** — every run keyed by `{stage, window, data_version}`; re-runs are safe and produce identical challengers (seed pinned).
- **Watermarks** — `learning_state` table tracks `last_attributed_at`, `last_retrained_at`, `active_champion_version` per model.
- **Rollback-ready** — every promotion keeps the prior version pinned; one call reverts.
- **Off the hot path** — all stages are batch/scheduled; heavy jobs run on the retrain cluster and never slow live outreach.
- **Langfuse trace** — every stage traced: attribution breakdowns, challenger-vs-champion deltas, eval verdicts, promotion decisions, drift alerts.
- **Cost discipline** — retraining is periodic, not per-token; fine-tune small local models where possible; track **cost-per-model-improvement**.

---

## §WL2-6.9 — Import & configuration notes

1. **Import** each workflow (WL2–WL6) as a separate n8n workflow sharing the `learning_state` + registry tables.
2. **Credentials:** Postgres (`outcome_log`, feature store, registry), Neo4j, Qdrant, LiteLLM, Langfuse, Rep Cockpit approval API, alerting channel.
3. **Schedules:** WL2 `0 2 * * *`; WL3 `0 3 * * 1` + threshold env `RETRAIN_MIN_OUTCOMES`; WL4/WL5 event-driven; WL6 `*/15 * * * *` + stream.
4. **Gates config:** `EVAL_MIN_SAMPLE`, `EVAL_CONFIDENCE`, `HIGH_IMPACT_MODELS[]` (route to Cockpit), `AUTO_PROMOTE_MODELS[]`.
5. **First-run order:** WL2 must have ≥1 completed attribution window before WL3's first cycle — enforce via watermark check.

> **Build-order rule (from L-LEARN §L.6):** WL1 harvesting first and immediately; WL2 attribution before any retrainer; champion/challenger by default; human-gated promotion for high-impact, auto for low-risk. Velocity with a seatbelt.

---

## §WL2-6.10 — Where this sits in the flywheel

```
   FLOW-WL1  ─ harvest every outcome ─▶  outcome_log
                                            │
        ┌───────────────────────────────────┘
        ▼
   WL2 attribute ─▶ WL3 retrain ─▶ WL4 prove ─▶ WL5 promote ─┐
        ▲                                                     │
        │                          writeback (version bump)   │
        └──────────  L-GEN · [6] scoring · [5] persona · ─────┘
                     [7] copy · L-OMNI bandit · Source Genome
                                     ▲
                              WL6 drift watch (continuous)
```

**This closes the fourth and final ADD-GAP gap.** Dominion now finds → enriches → reaches → converses → qualifies → books → hands off → **and learns from every outcome to do all of it better next cycle.** The flywheel turns.
