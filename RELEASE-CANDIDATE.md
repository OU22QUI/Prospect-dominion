# Prospect Dominion Release Candidate

## Release identity

- Product: Prospect Dominion
- Candidate: v1.0.0-rc1
- Release type: pilot-ready software and publishable static demo
- Public hosting target: GitHub Pages for `demo/`
- Technical hosting target: customer-owned Docker Compose environment

## Verified in this candidate

- FastAPI application and SQLite operational store
- Authenticated API routes and role checks
- Production configuration guardrails
- Runtime branding via environment configuration
- Full core Compose startup
- API container healthcheck
- Garage v1 configuration startup
- Redis, Qdrant, Postgres, Neo4j, LiteLLM, OSINT, workers, Caddy, Mem0, n8n, and Crawl4AI startup path
- Deterministic deployment verification
- Demo seed and workflow progression
- Public-demo secret scan
- Customer environment validation
- Clean Compose teardown

## Verification commands

```powershell
cd "C:\Users\pc\Desktop\THE PROSPECT DOMINION"
python scripts/validate_customer_config.py --env-file deploy/customer.env.example --check-public-demo
python -m py_compile scripts/validate_customer_config.py scripts/verify_deployment.py scripts/verify_local.py
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core config --quiet
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --wait
$env:PD_API_KEY="dev-local-key"
$env:PD_BASE_URL="http://127.0.0.1:8010"
python scripts/verify_deployment.py
cd services/api
python -m pytest -q
```

## Release boundary

This candidate is suitable for public demonstration, tester review, technical sales, and controlled customer pilots.

It is not a claim of multi-tenant SaaS readiness. The following remain later product phases:

- multi-tenant isolation
- customer user administration
- billing
- managed remote infrastructure provisioning
- automated backup and restore
- customer workflow administration UI

## Publishing requirement

The GitHub Pages workflow is ready, but a Git remote and GitHub Pages repository are required to produce the external URL. This workspace currently has no configured Git remote, so publication cannot be completed locally without repository ownership and access.
