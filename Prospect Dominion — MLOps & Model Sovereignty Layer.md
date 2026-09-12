# \# 🧬 Prospect Dominion — MLOps \& Model Sovereignty Layer

# &#x20; 

# &#x20; > \*\*Module ⑨ · MLOPS v1.0 · Elite Edge Layer\*\*

# &#x20; > The platform beneath the flywheel. \*\*L-LEARN\*\* defines \*what\* to learn and \*\*WL2-6\*\* \*when\* to learn it; MLOPS is \*where models are trained, versioned, evaluated, served, and watched\* — entirely on the client's own infrastructure. This is the module that turns "prompted LLM calls" into \*\*owned, fine-tuned, drift-monitored models that no competitor can copy and no vendor can revoke.\*\*

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.0 — Why This Module Exists

# &#x20; 

# &#x20; The learning loop is specified but has no ground to stand on. Three upstream references dangle:

# &#x20; - \*\*L-LEARN §L.5\*\* names four retrainers (scoring, ICP, persona, copy) but not the pipeline that runs them.

# &#x20; - \*\*WL2-6\*\* references a \*champion registry\*, \*shadow serving\*, and \*rollback\* with no registry or serving substrate defined.

# &#x20; - \*\*GOV ⑦ / HITL ⑧\*\* gate \*model promotions\* but assume something to promote \*to\* and \*from\*.

# &#x20; 

# &#x20; MLOPS is that substrate: a \*\*model registry\*\* (versioned, rollback-ready), a \*\*fine-tuning pipeline\*\* (LoRA on closed-won), an \*\*eval harness\*\* (offline backtest + champion/challenger shadow), \*\*serving\*\* (LiteLLM → vLLM/Ollama), and \*\*drift instrumentation\*\* (Langfuse + metrics). It is the deepest expression of sovereignty in the whole system: the client's data trains the client's models on the client's hardware.

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.1 — Layer Stack

# &#x20; 

# &#x20; ```

# &#x20; ┌──────────────────────────────────────────────────────────────────────┐

# &#x20; │  M6  DRIFT SENTINEL     Accuracy decay · calibration slip · reply erosion│

# &#x20; ├──────────────────────────────────────────────────────────────────────┤

# &#x20; │  M5  SERVING            LiteLLM router → vLLM / Ollama · shadow lane     │

# &#x20; ├──────────────────────────────────────────────────────────────────────┤

# &#x20; │  M4  REGISTRY           Versioned models · ICP-as-Code · personas · rollback│

# &#x20; ├──────────────────────────────────────────────────────────────────────┤

# &#x20; │  M3  EVAL HARNESS       Offline backtest · champion/challenger · poisoning│

# &#x20; ├──────────────────────────────────────────────────────────────────────┤

# &#x20; │  M2  TRAINING           4 retrainers · LoRA fine-tune · feature store    │

# &#x20; ├──────────────────────────────────────────────────────────────────────┤

# &#x20; │  M1  DATA CONTRACT      outcome\_log · attribution · win/loss embeddings  │

# &#x20; └──────────────────────────────────────────────────────────────────────┘

# &#x20; ```

# &#x20; 

# &#x20; M1 reads from the flywheel's ground truth (WL1); M2–M4 produce and store challengers; M5 serves champion + shadow; M6 watches and triggers rollback. GOV/HITL sit across M4→M5 as the promotion gate.

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.2 — Squads (realizes L-LEARN §L.7 pods on real infra)

# &#x20; 

# &#x20; | Squad | Owns | Stack |

# &#x20; |---|---|---|

# &#x20; | \*\*Model Trainer\*\* | runs the four retrainers; produces challengers | MLOps pipeline · LiteLLM · local LoRA fine-tuning |

# &#x20; | \*\*Evaluator\*\* | offline backtest · champion/challenger shadow · significance + poisoning checks | eval harness · Langfuse |

# &#x20; | \*\*Registrar\*\* | versions every model/ICP/persona/playbook; rollback-ready; serves lineage | model registry (Postgres `model\_version` + object store) |

# &#x20; | \*\*Serving Squad\*\* | routes production + shadow inference; zero-downtime version swaps | LiteLLM router → vLLM/Ollama |

# &#x20; | \*\*Drift Sentinel\*\* | monitors accuracy decay, calibration slip, persona drift, reply-rate erosion | metrics · Langfuse · alerting |

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.3 — Data Contract (M1)

# &#x20; 

# &#x20; MLOPS trains \*\*only\*\* on flywheel ground truth — never on ad-hoc pulls.

# &#x20; 

# &#x20; | Store | Provides |

# &#x20; |---|---|

# &#x20; | \*\*Postgres\*\* `outcome\_log` (WL1) | append-only labels: win/loss/no-show/reply/bounce/DQ |

# &#x20; | \*\*Postgres\*\* `attribution` (WL2) | which signal/copy/persona/channel caused which outcome |

# &#x20; | \*\*Qdrant\*\* win/loss embeddings | winning vs. losing messages + transcripts — "what resonates" |

# &#x20; | \*\*Feature store\*\* | `predicted-score → actual-outcome` pairs for the scoring retrainer |

# &#x20; 

# &#x20; Every training run records its exact input snapshot hash → any model is reproducible and auditable (feeds GOV's ledger).

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.4 — Training Pipeline (M2) — the four retrainers, industrialized

# &#x20; 

# &#x20; | Retrainer | Produces | Method |

# &#x20; |---|---|---|

# &#x20; | \*\*Predictive Scoring\*\* | new lead-scoring challenger | supervised on `predicted→actual` pairs; SHAP attributions preserved for explainability; target 78–88% accuracy band, improving calibration |

# &#x20; | \*\*ICP Curator\*\* | PR-style diff to ICP-as-Code | closed-won vs. closed-lost trait analysis → weight changes (highest-leverage; human-gated) |

# &#x20; | \*\*Persona / Psychographic\*\* | re-clustered segment map | re-cluster on new behavioral data; refine signal→persona→tone mapping |

# &#x20; | \*\*Copy / Message Tuner\*\* | copy-variant reweights + fine-tuned generation | LoRA fine-tune on winning messages; retrieval of "what resonates" from Qdrant |

# &#x20; 

# &#x20; \*\*Sovereign fine-tuning:\*\* generation models are \*\*LoRA-fine-tuned locally\*\* on the client's closed-won corpus, served through vLLM/Ollama behind LiteLLM. No prompts, no proprietary data, and no fine-tunes ever leave the client's infrastructure. \*The data flywheel is the moat; this module is where the moat is dug.\*

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.5 — Eval Harness (M3) — the safety valve, mechanized

# &#x20; 

# &#x20; Every challenger must clear the gate before it can be promoted (GOV ⑦ / HITL ⑧ own the human step; MLOPS owns the machine steps):

# &#x20; 

# &#x20; 1. \*\*Offline backtest.\*\* Scored against a held-out set of recent outcomes; must beat the incumbent champion on the target metric.

# &#x20; 2. \*\*Champion/Challenger (shadow).\*\* The challenger scores \*live traffic in parallel without acting\* until it proves out on real data.

# &#x20; 3. \*\*Significance + poisoning checks.\*\* Statistical significance before promotion; anomaly/poisoning detection guards against a bad or adversarial outcome batch corrupting a model.

# &#x20; 

# &#x20; Only a challenger that clears all three becomes \*promotable\* — at which point low-risk auto-promotes and high-impact routes to HITL's promotion queue.

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.6 — Model Registry (M4) — versioned \& rollback-ready

# &#x20; 

# &#x20; The `model\_version` registry is the source of truth for \*what is live\*:

# &#x20; 

# &#x20; - Versions \*\*every\*\* learnable asset: scoring models, ICP-as-Code versions, persona clusters, copy models, channel/playbook policies.

# &#x20; - Each version stores: training-input hash, eval scores, promotion verdict + operator (from HITL), and a \*\*one-click rollback\*\* pointer to its predecessor.

# &#x20; - A version bump to ICP-as-Code shifts \*\*all discovery behavior with no redeploy\*\* — the machine redirects its own targeting (A2 autonomy), with the human on the high-impact switch.

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.7 — Serving \& Drift (M5 · M6)

# &#x20; 

# &#x20; \*\*Serving (M5).\*\* All inference flows through \*\*LiteLLM\*\* (INFRA L3), which routes to local \*\*vLLM/Ollama\*\* for fine-tuned models and holds a \*\*shadow lane\*\* so challengers score live traffic without acting. Version swaps are zero-downtime — the registry flips the champion pointer; LiteLLM routes accordingly.

# &#x20; 

# &#x20; \*\*Drift Sentinel (M6).\*\* Continuously watches (via Langfuse + metrics): accuracy decay, calibration slip, persona/segment drift, and reply-rate erosion. On a drift alarm it emits `drift.detected` → GOV's Kill Plane can \*\*auto-roll back to the prior champion\*\* while a fresh challenger is trained. No silent drift ever reaches production.

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.8 — Event Contracts

# &#x20; 

# &#x20; \*\*Consumes:\*\* `outcome.logged` (WL1), `retrain.due` (WL3 schedule), `model.approved` / `model.rejected` (HITL ⑧).

# &#x20; 

# &#x20; \*\*Emits:\*\* `challenger.ready` (→ eval), `model.promotable` (→ GOV/HITL gate), `model.promoted` (→ serving swap + WL6 watch), `drift.detected` (→ GOV Kill Plane), `model.rolledback`.

# &#x20; 

# &#x20; All carry model lineage + `thread\_id` provenance where applicable, so a served decision traces to the exact model version and training snapshot that produced it.

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.9 — Service Endpoints (wire to INFRA v1.0)

# &#x20; 

# &#x20; | Service | Role |

# &#x20; |---|---|

# &#x20; | `litellm:4000` | inference router (champion + shadow lanes) → vLLM/Ollama |

# &#x20; | `vllm` / `ollama` | local serving of fine-tuned sovereign models |

# &#x20; | `mlops-svc` | retrainer orchestration + fine-tune jobs + eval harness |

# &#x20; | `registry-svc` | `model\_version` registry + rollback API + lineage |

# &#x20; | `langfuse:3000` | eval traces + drift telemetry |

# &#x20; 

# &#x20; All map to docker-compose service names in \*\*INFRA v1.0\*\* (L3 Intelligence + L0 Observability).

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.10 — Roadmap

# &#x20; 

# &#x20; - \*\*Phase 0 — Registry + serving spine.\*\* Stand up `model\_version` registry and LiteLLM→vLLM/Ollama serving with a champion pointer. \*Exit: every model in prod is versioned and rollback-ready.\*

# &#x20; - \*\*Phase 1 — Eval harness.\*\* Offline backtest + champion/challenger shadow lane + significance/poisoning gates. \*Exit: no model acts on prod traffic until it proves out in shadow.\*

# &#x20; - \*\*Phase 2 — Sovereign fine-tuning.\*\* Local LoRA on closed-won copy; scoring retrainer on `predicted→actual`. \*Exit: the client serves its own fine-tuned models on its own hardware.\*

# &#x20; - \*\*Phase 3 — Drift + auto-rollback.\*\* Drift Sentinel live; `drift.detected` → auto-rollback + retrain trigger. \*Exit: no silent drift; the system heals its own models.\*

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; ## §M.11 — Elite Differentiators

# &#x20; 

# &#x20; - \*\*Own models, not rented ones.\*\* Fine-tuned on the client's closed-won, served on the client's hardware — the moat is a data flywheel no competitor can copy and no vendor can switch off.

# &#x20; - \*\*Prove-in-shadow-first.\*\* Champion/challenger by default means no model touches a real prospect until it has beaten the incumbent on live traffic. This single discipline prevents most self-improvement disasters.

# &#x20; - \*\*Reproducible to the row.\*\* Every model records its training-snapshot hash, eval scores, and promotion verdict — any decision is traceable to the exact model and data that made it.

# &#x20; - \*\*Explainability preserved through retraining.\*\* SHAP-style attributions survive every scoring retrain, so sales always sees \*why\* — the model gets smarter without going darker.

# &#x20; - \*\*Self-healing.\*\* Drift is detected, rolled back, and retrained automatically — the system's intelligence degrades gracefully and recovers on its own, never silently.

# &#x20; 

# &#x20; ---

# &#x20; 

# &#x20; \*MLOPS v1.0 · Module ⑨ of the Prospect Dominion Elite Edge · house style aligned with GOV ⑦, HITL ⑧, and the Workflow Suite Index · realizes L-LEARN §L.5–L.7 and WL2-6 on real infrastructure · resolves the model registry, shadow serving, and rollback references.\*

# &#x20; 

