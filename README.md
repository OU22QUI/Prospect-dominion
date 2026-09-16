# Prospect Dominion

This workspace contains the Prospect Dominion design set and a minimal runnable starter scaffold for the sovereign infrastructure described in the documents.

## What's included

- `docker-compose.yml` with the core data, intelligence, orchestration, and optional overlays
- `docker-compose.comms.yml` and `docker-compose.observability.yml`
- Minimal FastAPI services for the API, OSINT worker, and supporting workers
- Local environment template at `.env.example`

## Quickstart

1. Copy `.env.example` to `.env` and fill in secrets.
2. For local development, keep the defaults in `.env` and ensure `APP_ENV=local` is set. For production, set `APP_ENV=production` and provide real values for `JWT_SECRET`, `PD_API_KEY`, and `PUBLIC_BASE_URL`.
3. If local ports are already occupied, the default local host ports are intentionally non-conflicting: `API_PORT=8010`, `OSINT_PORT=8081`, `REDIS_PORT=6380`, and `QDRANT_PORT=6335`.
4. Start the data and core services from the repo root:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build
   ```
5. Verify the core services are healthy:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core ps
   ```
6. Run the deterministic deployment verification:
   ```bash
   python scripts/verify_deployment.py
   ```
   This verifies service state, API health and readiness, authentication boundaries, branding, demo seeding, and workflow advancement. Add `--teardown` to stop the stack after validation.
7. For a customer deployment, copy and validate the customer template:
   ```bash
   copy deploy\customer.env.example .env
   python scripts/validate_customer_config.py --env-file .env --check-public-demo
   ```
   Use `--production` for a production-scoped configuration. See [Prospect-Dominion-Customer-Deployment.md](Prospect-Dominion-Customer-Deployment.md).
8. Run the API directly for the local product workflow using the safe launcher:
   ```bash
   cd services/api
   $env:PD_API_KEY = "dev-local-key"
   python run_local.py
   ```
   To force a specific port, set `PD_PORT` first:
   ```bash
   $env:PD_PORT = "8123"
   $env:PD_API_KEY = "dev-local-key"
   python run_local.py
   ```
9. Confirm the service is ready at the selected local port:
   ```bash
   curl http://127.0.0.1:8123/ready
   ```
10. Seed the local dataset:
   ```bash
   curl -X POST http://127.0.0.1:8123/demo/seed -H "Authorization: Bearer dev-local-key"
   ```

For authenticated API calls, use the same bearer token for routes like `/threads`, `/dashboard`, and `/events`.

## Production hardening checklist

The service is intentionally permissive in `APP_ENV=local`, but production mode enforces stricter requirements.

- `APP_ENV=production`
- `PD_API_KEY` must be set and prefixed with `prod-`
- `JWT_SECRET` must be set
- `PUBLIC_BASE_URL` must be set
- use strong values in `.env` and never commit secrets to source control
- rotate keys and secrets before any live deployment

This keeps the local starter usable while ensuring a real deployment does not run with missing or weak credentials.

## Local endpoints

- Ready: http://127.0.0.1:8010/ready
- Health: http://127.0.0.1:8010/health
- Dashboard: http://127.0.0.1:8010/
- Threads: http://127.0.0.1:8010/threads
- Branding: http://127.0.0.1:8010/branding
- Qdrant: http://127.0.0.1:6335/readyz

> If 8000 is already in use by another local process, the launcher selects the next available port automatically and prints it. Use `PD_PORT` to pin a specific port when needed.

## Verified project state

Fresh validation on 2026-09-14:

- `cd services/api` and `python -m pytest -q tests/test_api.py`
  - Result: `11 passed in 0.93s`
- `cd ..` and `python scripts/demo_local.py`
  - Result: `health 200`, `ready 200`, `seed 200`, `dashboard 200`
  - Verified checks: database ok, qdrant ok, redis ok
  - Local API port: `8123`

This confirms the app-layer runtime and Compose deployment are operational for local demos and workflow validation. Use `python scripts/verify_deployment.py` as the current source of truth for a complete deployment check.

## Commercial source of truth

The publicly sellable product layer is documented in the commercial package and sales assets below:

- [Prospect-Dominion-Commercial-Playbook.md](Prospect-Dominion-Commercial-Playbook.md)
- [Prospect-Dominion-Pricing-Overview.md](Prospect-Dominion-Pricing-Overview.md)
- [Prospect-Dominion-Pilot-Overview.md](Prospect-Dominion-Pilot-Overview.md)
- [Prospect-Dominion-Deployment-Offer.md](Prospect-Dominion-Deployment-Offer.md)
- [Prospect-Dominion-White-Label-Offer.md](Prospect-Dominion-White-Label-Offer.md)
- [Prospect-Dominion-Sales-Assets.md](Prospect-Dominion-Sales-Assets.md)
- [Prospect-Dominion-Product-Brief.md](Prospect-Dominion-Product-Brief.md)
- [Prospect-Dominion-Customer-One-Pager.md](Prospect-Dominion-Customer-One-Pager.md)

These documents define the approved commercial positioning, pricing posture, pilot structure, deployment framing, white-label architecture, and sales-ready product narrative for Prospect Dominion.

## Notes

This project is now a working local starter for the Prospect Dominion product layer rather than a static doc-only scaffold. It includes a stable local API, SQLite persistence, workflow progression, and dockerized backing services. The default host port for Qdrant is set to 6335 because 6333 is already occupied in many local development environments.
