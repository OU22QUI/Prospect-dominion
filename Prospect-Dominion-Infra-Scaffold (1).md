# 🐳 Prospect Dominion — Infrastructure Scaffold

> **Module INFRA v1.0** — Sovereign Deployment Substrate (Docker Compose → K8s)
> **Baseline:** DATA v1.0 · FullStack Build Prompt · ADD-GAP §14 (Platform/Infra Sovereignty) · Blueprint v1.1
> **Purpose:** The runnable infrastructure that boots the entire sovereign stack — every store in DATA v1.0 and every service in the layer stack — locally with `docker compose up`, then lifts to Kubernetes unchanged.
> **House style:** layer stack · squads · §-numbering · event-driven · workflows · roadmap · elite differentiators.

---

## §0. Design Principles

1. **One command to sovereignty.** `docker compose up` brings the whole stack live on a single host; nothing mandatory reaches a third-party SaaS.
2. **Boot order is a contract, not a hope.** Healthchecks + `depends_on: condition: service_healthy` enforce the dependency DAG. Stores before services; LiteLLM before any agent; Postal warmup before any send path.
3. **Config is environment, secrets are a vault.** No secret is ever baked into an image or committed. `.env` for local; the secrets vault (§7) for anything real.
4. **Every service is observable from birth.** Each container exposes `/health` and metrics; Langfuse + Prometheus/Loki are up before the services they watch.
5. **Compose and K8s share one topology.** Service names, ports, env keys, and volumes are identical across both so promotion is mechanical, not a rewrite.
6. **Stateful data lives on named volumes only.** Bind mounts are for config; volumes are for data. Backups (§8) target volumes exclusively.

---

## §1. Topology at a Glance

| Layer | Services | Compose profile |
|---|---|---|
| **L0 Observability** | Langfuse, Prometheus, Grafana, Loki, secrets vault | `observability` |
| **L1 Delivery/Comms** | Postal (MTA + warmup), Fonoster, LiveKit, Domain Pool Mgr | `comms` |
| **L2 Memory/Knowledge** | Postgres, Neo4j, Qdrant, Mem0, Garage (S3), Redis | `data` |
| **L3 Intelligence** | LiteLLM, Crawl4AI, OSINT/Dork, Email-Intel, Psychographic, Conversation-Intel, Scoring/ML, Reranker | `intel` |
| **L4 Orchestration** | n8n, `services/api`, Caddy (edge), workers | `core` |

> Profiles let you boot subsets: `docker compose --profile data --profile observability up` for a data-layer-only bring-up during migration from `aethonex.db`.

---

## §2. Boot-Order DAG

```
secrets-vault ─┐
               ├─▶ postgres ─┬─▶ api ─┬─▶ n8n ─▶ workers
prometheus ────┤            │        │
loki ──────────┤   neo4j ───┤        ├─▶ intel services (osint, email-intel,
grafana ───────┘   qdrant ──┤        │      psychographic, conversation-intel,
langfuse ──▶ (needs pg)     │        │      scoring, reranker)
                   redis ───┤        │
                   garage ──┘        └─▶ litellm ─▶ (all agent/intel calls)
                                     
postal ─▶ warmup-mesh ─▶ (gate) ─▶ outreach send path
fonoster / livekit ─▶ voice path (after O-0 consent gate)
```

**Hard gates encoded in healthchecks & startup guards:**
- `litellm` must be `healthy` before any intel/agent service accepts work.
- `postal` + `warmup-mesh` must report an aged, reputation-cleared domain before `outreach` will send (L-SEND precedence).
- `api` refuses traffic until `postgres` migrations have applied cleanly.

---

## §3. `docker-compose.yml` (Core)

```yaml
name: prospect-dominion

x-logging: &default-logging
  driver: json-file
  options: { max-size: "10m", max-file: "3" }

x-healthcheck-defaults: &hc
  interval: 10s
  timeout: 5s
  retries: 12
  start_period: 20s

networks:
  pd-net: { driver: bridge }

volumes:
  pg-data:
  neo4j-data:
  qdrant-data:
  garage-data:
  garage-meta:
  redis-data:
  langfuse-pg:
  postal-data:
  n8n-data:
  grafana-data:
  loki-data:
  prometheus-data:

services:

  # ── L2 Memory / Knowledge ───────────────────────────────
  postgres:
    image: postgres:16-alpine
    profiles: ["data", "core"]
    environment:
      POSTGRES_USER: ${PG_USER}
      POSTGRES_PASSWORD: ${PG_PASSWORD}
      POSTGRES_DB: ${PG_DB}
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ./migrations/postgres:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PG_USER} -d ${PG_DB}"]
      <<: *hc
    networks: [pd-net]
    logging: *default-logging

  neo4j:
    image: neo4j:5-community
    profiles: ["data", "core"]
    environment:
      NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j-data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:7474 || exit 1"]
      <<: *hc
    networks: [pd-net]
    logging: *default-logging

  qdrant:
    image: qdrant/qdrant:latest
    profiles: ["data", "core"]
    volumes:
      - qdrant-data:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "bash -c ':> /dev/tcp/localhost/6333' || exit 1"]
      <<: *hc
    networks: [pd-net]
    logging: *default-logging

  garage:
    image: dxflrs/garage:v1.0.0
    profiles: ["data", "core"]
    volumes:
      - garage-data:/data
      - garage-meta:/meta
      - ./infra/garage/garage.toml:/etc/garage.toml:ro
    networks: [pd-net]
    logging: *default-logging

  redis:
    image: redis:7-alpine
    profiles: ["data", "core"]
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD}"]
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      <<: *hc
    networks: [pd-net]
    logging: *default-logging

  mem0:
    image: mem0/mem0:latest
    profiles: ["data", "core"]
    environment:
      MEM0_VECTOR_STORE: qdrant
      QDRANT_URL: http://qdrant:6333
      MEM0_LLM_BASE_URL: http://litellm:4000
    depends_on:
      qdrant: { condition: service_healthy }
    networks: [pd-net]
    logging: *default-logging

  # ── L3 Intelligence ─────────────────────────────────────
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    profiles: ["intel", "core"]
    environment:
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      DATABASE_URL: postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}
      LANGFUSE_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY}
      LANGFUSE_SECRET_KEY: ${LANGFUSE_SECRET_KEY}
      LANGFUSE_HOST: http://langfuse:3000
    volumes:
      - ./infra/litellm/config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    depends_on:
      postgres: { condition: service_healthy }
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:4000/health/liveliness || exit 1"]
      <<: *hc
    networks: [pd-net]
    logging: *default-logging

  crawl4ai:
    image: unclecode/crawl4ai:latest
    profiles: ["intel", "core"]
    shm_size: "1gb"
    networks: [pd-net]
    logging: *default-logging

  # Intel microservices (osint, email-intel, psychographic,
  # conversation-intel, scoring, reranker) share this template:
  osint:
    build: { context: ./services/osint }
    profiles: ["intel", "core"]
    environment:
      LITELLM_BASE_URL: http://litellm:4000
      PG_DSN: postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}
      CRAWL4AI_URL: http://crawl4ai:11235
    depends_on:
      litellm: { condition: service_healthy }
      postgres: { condition: service_healthy }
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8080/health || exit 1"]
      <<: *hc
    networks: [pd-net]
    logging: *default-logging

  # ── L4 Orchestration ────────────────────────────────────
  api:
    build: { context: ./services/api }
    profiles: ["core"]
    environment:
      PG_DSN: postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}
      NEO4J_URL: bolt://neo4j:7687
      QDRANT_URL: http://qdrant:6333
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      LITELLM_BASE_URL: http://litellm:4000
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      postgres: { condition: service_healthy }
      neo4j: { condition: service_healthy }
      qdrant: { condition: service_healthy }
      redis: { condition: service_healthy }
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8000/health || exit 1"]
      <<: *hc
    networks: [pd-net]
    logging: *default-logging

  n8n:
    image: n8nio/n8n:latest
    profiles: ["core"]
    environment:
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_DATABASE: ${PG_DB}
      DB_POSTGRESDB_USER: ${PG_USER}
      DB_POSTGRESDB_PASSWORD: ${PG_PASSWORD}
      N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY}
      WEBHOOK_URL: ${PUBLIC_BASE_URL}
      GENERIC_TIMEZONE: UTC
    volumes:
      - n8n-data:/home/node/.n8n
      - ./workflows:/workflows:ro
    depends_on:
      postgres: { condition: service_healthy }
      api: { condition: service_healthy }
    networks: [pd-net]
    logging: *default-logging

  workers:
    build: { context: ./services/workers }
    profiles: ["core"]
    environment:
      PG_DSN: postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      LITELLM_BASE_URL: http://litellm:4000
    depends_on:
      api: { condition: service_healthy }
      redis: { condition: service_healthy }
    networks: [pd-net]
    logging: *default-logging

  caddy:
    image: caddy:2-alpine
    profiles: ["core"]
    ports: ["80:80", "443:443"]
    volumes:
      - ./infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
    depends_on:
      api: { condition: service_healthy }
    networks: [pd-net]
    logging: *default-logging
```

> The `postal`, `fonoster`, `livekit`, `langfuse`, `prometheus`, `grafana`, and `loki` services follow in `docker-compose.comms.yml` and `docker-compose.observability.yml` (§4–§5) so the core file stays readable and profiles compose cleanly.

---

## §4. Comms Overlay (`docker-compose.comms.yml`)

```yaml
services:
  postal:
    image: ghcr.io/postalserver/postal:latest
    profiles: ["comms"]
    environment:
      POSTAL_SIGNING_KEY_PATH: /config/signing.key
      MAIN_DB_HOST: postgres
      MESSAGE_DB_HOST: postgres
    volumes:
      - postal-data:/opt/postal/config
      - ./infra/postal:/config:ro
    depends_on:
      postgres: { condition: service_healthy }
    networks: [pd-net]

  warmup-mesh:
    build: { context: ./services/warmup-mesh }
    profiles: ["comms"]
    environment:
      POSTAL_API_URL: http://postal:5000
      PG_DSN: postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}
    depends_on:
      postal: { condition: service_started }
    networks: [pd-net]

  fonoster:
    image: fonoster/fonoster:latest
    profiles: ["comms"]
    networks: [pd-net]

  livekit:
    image: livekit/livekit-server:latest
    profiles: ["comms"]
    command: ["--config", "/etc/livekit.yaml"]
    volumes:
      - ./infra/livekit/livekit.yaml:/etc/livekit.yaml:ro
    networks: [pd-net]
```

> **L-SEND gate:** `outreach` (a worker) queries `warmup-mesh` for a domain whose reputation has *aged past threshold* before it will send. No aged domain → no send. This is enforced in code, not just documented.

---

## §5. Observability Overlay (`docker-compose.observability.yml`)

```yaml
services:
  langfuse:
    image: langfuse/langfuse:latest
    profiles: ["observability"]
    environment:
      DATABASE_URL: postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/langfuse
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      SALT: ${LANGFUSE_SALT}
      NEXTAUTH_URL: ${PUBLIC_BASE_URL}/langfuse
    depends_on:
      postgres: { condition: service_healthy }
    networks: [pd-net]

  prometheus:
    image: prom/prometheus:latest
    profiles: ["observability"]
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks: [pd-net]

  loki:
    image: grafana/loki:latest
    profiles: ["observability"]
    volumes: [loki-data:/loki]
    networks: [pd-net]

  grafana:
    image: grafana/grafana:latest
    profiles: ["observability"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./infra/grafana/provisioning:/etc/grafana/provisioning:ro
    networks: [pd-net]
```

---

## §6. `.env.example`

```dotenv
# ── Postgres ──
PG_USER=aethonex
PG_PASSWORD=change-me-strong
PG_DB=prospect_dominion
# ── Neo4j ──
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me-strong
# ── Redis ──
REDIS_PASSWORD=change-me-strong
# ── LiteLLM ──
LITELLM_MASTER_KEY=sk-local-change-me
# ── Langfuse ──
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_NEXTAUTH_SECRET=change-me
LANGFUSE_SALT=change-me
# ── App ──
JWT_SECRET=change-me
N8N_ENCRYPTION_KEY=change-me
GRAFANA_PASSWORD=change-me
PUBLIC_BASE_URL=https://app.localhost
```

> **Rule:** `.env` is git-ignored. `.env.example` is committed with placeholders only. Real secrets flow from the vault (§7) into the runtime, never onto disk in plaintext beyond the local dev machine.

---

## §7. Secrets Vault

- **Local dev:** `.env` + docker secrets is acceptable.
- **Staging/prod:** an **Infisical** or **HashiCorp Vault** container (self-hosted, sovereign) injects secrets at runtime. Compose reads them via `env_file` generated on boot; K8s reads them via the vault CSI driver.
- **Rotation:** LiteLLM master key, Postal signing key, and JWT secret rotate on a schedule; rotation is an n8n workflow that writes new values to the vault and triggers a rolling restart.

---

## §8. Backups & Disaster Recovery

| Target | Method | Cadence | Destination |
|---|---|---|---|
| Postgres | `pg_dump` (logical) + WAL archiving | hourly WAL, nightly full | Garage bucket `backups/pg/` |
| Neo4j | `neo4j-admin database dump` | nightly | Garage `backups/neo4j/` |
| Qdrant | snapshot API | nightly | Garage `backups/qdrant/` |
| Garage | cross-node replication (RF=3 in cluster) | continuous | second Garage zone |
| Volumes | `restic` encrypted snapshots | nightly | offsite Garage / cold storage |

> **Restore drill:** a quarterly n8n workflow spins an ephemeral stack, restores last night's backups, runs a smoke suite, and reports pass/fail to the Cockpit. A backup you haven't restored is a rumor, not a backup.

---

## §9. Kubernetes Lift

Once Compose is stable, promotion is mechanical:

1. **`kompose convert`** as a starting skeleton, then hand-tune.
2. **Stores → StatefulSets** with PVCs (Postgres, Neo4j, Qdrant, Garage, Redis); **stateless services → Deployments + HPA**.
3. **Service names are preserved**, so intra-cluster DNS (`postgres`, `litellm`, `api`) resolves identically — zero env rewrites.
4. **Ingress** replaces Caddy (nginx-ingress or Traefik) with the same routing table.
5. **Secrets** move to the vault CSI driver; **config** to ConfigMaps generated from the same `./infra/**` files.
6. **Autoscale the send + intel tiers** independently; keep stores vertically scaled with read replicas for Postgres.

> Namespaces per tenant enable the **sovereign self-hosted license** (GTM ladder rung 3): each client gets an isolated namespace or an entirely isolated cluster from the same manifests.

---

## §10. Bring-Up Runbook

```bash
# 1. Data + observability first (migration target for aethonex.db)
cp .env.example .env && $EDITOR .env
docker compose --profile data --profile observability up -d
docker compose logs -f postgres   # wait for "database system is ready"

# 2. Apply migrations (idempotent)
docker compose run --rm api npm run migrate

# 3. Intelligence tier (needs LiteLLM healthy)
docker compose --profile intel up -d

# 4. Core orchestration
docker compose --profile core up -d

# 5. Comms LAST — warmup must age before any send
docker compose --profile comms up -d

# 6. Verify end-to-end: hello-world event flows and is traced in Langfuse
curl -s https://app.localhost/health | jq
```

**Exit gate (matches FullStack Phase 0):** stack boots, migrations apply, a hello-world event flows end-to-end and appears as a trace in Langfuse with a cost line.

---

## §11. Roadmap

| Wave | Deliverable | Exit gate |
|---|---|---|
| **W1** | Core compose (`data`+`observability`+`core`) boots on one host | migrations apply; health page green; one traced event |
| **W2** | Intel + comms overlays; warmup-mesh gate live | an aged-domain send is possible; a reply is classified on one thread |
| **W3** | Backups + restore drill automated via n8n | quarterly restore passes a smoke suite |
| **W4** | K8s manifests; single-tenant namespace deploy | same smoke suite passes in-cluster |
| **W5** | Multi-tenant namespaces for sovereign licensees | per-tenant isolation verified; one manifest set, N namespaces |

---

## §12. Elite Differentiators

- **Profile-composable sovereignty** — boot the data layer alone during SQLite migration, the full stack for production, or an isolated per-client cluster — from one manifest set.
- **Gate-as-code, not gate-as-doc** — the warmup/reputation and consent gates are healthchecks and startup guards, so an un-warmed domain physically *cannot* send.
- **Restore-verified backups** — an automated restore drill turns "we have backups" into "we have proven recovery," reported to the Cockpit.
- **Mechanical K8s promotion** — identical service names/ports/env across Compose and K8s make the lift a config move, not a rewrite — and the same manifests power the sovereign license tier.
- **One choke point, fully traced** — every model call routes through LiteLLM into Langfuse with cost, so infra spend is attributable per `thread_id` from day one.
```