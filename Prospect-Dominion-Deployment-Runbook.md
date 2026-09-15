# Prospect Dominion — Deployment and Demo Runbook

## Purpose
This runbook is for a clean local deployment and customer-facing demo of the Prospect Dominion stack. It is designed to reduce startup friction, avoid local port conflicts, and present a credible, working baseline to a buyer or pilot customer.

---

## Preconditions
Before running the stack, ensure:
- Docker Desktop or Docker Engine is installed and running
- Python 3.11 is installed
- the repo is cloned locally
- the current working directory is the repo root

The repo should be opened at:
- `C:\Users\pc\Desktop\THE PROSPECT DOMINION`

---

## 1) Environment defaults
The repo includes environment defaults in `.env.example` and the Compose stack is configured to avoid common local conflicts.

The working defaults are:
- `API_PORT=8010`
- `OSINT_PORT=8081`
- `REDIS_PORT=6380`
- `QDRANT_PORT=6335`
- `PD_PORT=8010`

These defaults are intentionally moved away from common occupied ports such as 6379, 8000, and 8080 to avoid local environment drift.

---

## 2) Set the local environment
From the repo root, set the environment explicitly before startup:

```powershell
cd "C:\Users\pc\Desktop\THE PROSPECT DOMINION"
$env:API_PORT="8010"
$env:OSINT_PORT="8081"
$env:REDIS_PORT="6380"
$env:PD_PORT="8010"
$env:PD_API_KEY="dev-local-key"
```

If you want a stricter production-like setup, use a production-scoped key and set `APP_ENV=production` with a valid `prod-` key prefix.

---

## 3) Clean the stack before startup
If you have stale containers or port collisions from earlier runs, stop and remove the stack first:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core down --remove-orphans
```

---

## 4) Start the stack
Run:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build
```

Then verify the services:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core ps --format 'table {{.Service}}\t{{.State}}\t{{.Ports}}'
```

Expected running services include:
- api
- caddy
- litellm
- mem0
- n8n
- neo4j
- osint
- postgres
- qdrant
- redis
- workers

---

## 5) Check runtime health
The API is available on:
- `http://127.0.0.1:8010/ready`

Use the valid bearer token:
- `Authorization: Bearer dev-local-key`

Example:

```powershell
python -c "import json, urllib.request; req=urllib.request.Request('http://127.0.0.1:8010/ready', headers={'Authorization':'Bearer dev-local-key'}); print(urllib.request.urlopen(req, timeout=10).status)"
```

Expected result:
- `200`

---

## 6) Check the dashboard route
The protected dashboard endpoint is:
- `http://127.0.0.1:8010/dashboard`

Example:

```powershell
python -c "import json, urllib.request; req=urllib.request.Request('http://127.0.0.1:8010/dashboard', headers={'Authorization':'Bearer dev-local-key'}); body=urllib.request.urlopen(req, timeout=10).read().decode(); data=json.loads(body); print(sorted(data.keys())); print(data.get('thread_count')); print(data.get('project'))"
```

Expected behavior:
- returns JSON data successfully
- includes keys such as `event_count`, `outcome_count`, `recent_outcomes`, `thread_count`, and `threads`

Without a bearer token, the endpoint is expected to return `401` as a secure response.

---

## 7) Run the repo smoke test
From the repo root, run:

```powershell
cd "C:\Users\pc\Desktop\THE PROSPECT DOMINION"
python scripts/demo_local.py
```

This script validates the main end-to-end flow:
- health endpoint
- readiness endpoint
- demo seed route
- dashboard route

Expected result: successful status responses for the key runtime checks.

---

## 8) Run the deployment verifier

From the repo root, run:

```powershell
python scripts/verify_deployment.py
```

The verifier checks that all core services are running, health-gated services are healthy, the API is ready, unauthenticated dashboard access is rejected, branding is available, demo data can be seeded, and a workflow thread can advance. Use `--teardown` to stop the core stack after validation.

---

## 9) Prepare a customer deployment

Use the customer-safe template and validator before handing an environment to a pilot customer:

```powershell
Copy-Item deploy/customer.env.example .env
python scripts/validate_customer_config.py --env-file .env --check-public-demo
```

For a production-scoped environment:

```powershell
python scripts/validate_customer_config.py --env-file .env --production --check-public-demo
```

See [Prospect-Dominion-Customer-Deployment.md](Prospect-Dominion-Customer-Deployment.md) for the customer initialization, update, and teardown procedure.

---

## 10) Local troubleshooting
If startup fails, check the following in order:

### Port conflicts
Use:

```powershell
netstat -ano | findstr :6379
netstat -ano | findstr :8000
netstat -ano | findstr :8080
```

If conflicts appear, stop the conflicting process or adjust the environment variables before restart.

### Docker stack stale state
Use:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core down --remove-orphans
```

Then rebuild:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build
```

### API readiness issues
Check:

```powershell
python -c "import json, urllib.request; req=urllib.request.Request('http://127.0.0.1:8010/ready', headers={'Authorization':'Bearer dev-local-key'}); print(urllib.request.urlopen(req, timeout=10).read().decode())"
```

---

## 11) Demo flow narrative
This is the recommended demo storyline for a customer or prospect:

1. The system is up and health-checked.
2. The API is protected and production-safe.
3. The dashboard presents operational structure and context.
4. The workflow layer can coordinate and enrich signal-driven actions.
5. Trust and governance are handled explicitly rather than implicitly.

This makes the demo feel like a real operating system rather than a toy script.

---

## 12) Final recommendation
Use this runbook for any customer or pilot handoff. It is the shortest path to a credible demo and the most reliable local deployment path in the current repo state.

The highest-leverage operational rule is simple:
- keep the stack on the non-conflicting defaults,
- verify readiness with the bearer token,
- treat the dashboard as a protected operational surface,
- and only demo the stack after the health flow is green.

---

## Key repo files
- [docker-compose.yml](docker-compose.yml)
- [.env.example](.env.example)
- [README.md](README.md)
- [services/api/app/main.py](services/api/app/main.py)
- [services/api/app/stores.py](services/api/app/stores.py)
- [services/api/run_local.py](services/api/run_local.py)
- [scripts/demo_local.py](scripts/demo_local.py)
