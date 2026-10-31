# Prospect Dominion Pilot Acceptance

## Executive statement

This document is the canonical acceptance contract for the current Prospect Dominion release. It defines the scope of the product as a single-customer pilot/deployment stack, not a general multi-tenant SaaS platform.

The current product is considered pilot-ready only when an operator can provision a customer environment, configure secrets and hostnames, run the stack, verify readiness, deliver a safe workflow, and complete a documented handover without discovering missing engineering pieces.

## Product boundary

Prospect Dominion is a governed signal-to-action workflow for one customer at a time. In scope for the current pilot:

- one customer deployment
- one Postgres-backed system of record
- one or two approved data sources
- operator approval before an external send
- controlled send workflow and outcome capture
- audit record of workflow events
- public demo for product explanation
- documented operator runbook and backup/restore path

Out of scope for this pilot:

- multi-tenancy
- self-service customer provisioning
- billing, subscription, or contract workflows
- universal AI orchestration
- broad public integrations
- white-label infrastructure as a core service
- extensive roadmap features not required for one customer workflow

## Required deployment model

The production stack requires:

- Docker and Docker Compose
- Python 3.11 for the API and validation scripts
- Postgres 16 for the governed store
- Redis for queue/task support
- customer-owned public hostname
- HTTPS/TLS termination via Caddy or equivalent reverse proxy
- Resend API key and webhook signing secret for outbound send and callback processing
- generated JWT secret and environment-specific runtime secrets
- a customer `.env` file managed outside source control

## Startup and readiness

Required commands:

```bash
cp deploy/customer.env.example .env
# replace placeholder values with real customer values
python scripts/validate_customer_config.py --env-file .env --production

docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build --wait
python scripts/verify_deployment.py
```

Expected outcome:

- API responds on `/ready` with `status="ready"`
- /health returns `{"status":"ok"}`
- required service set is running
- Postgres is healthy
- API can seed a workflow and advance it
- unauthorized access to protected routes is denied

## Authentication and authorization

The implemented production contract is:

- API key required for legacy shared-key routes
- server-issued RBAC via `/v1` routes
- production default role must be `viewer`
- writes require authenticated role checks, not caller-controlled role headers
- webhook validation must reject invalid or tenant-mismatched requests

The runtime must fail closed if required production variables are missing or invalid.

## Data and workflow acceptance

The deployment is accepted when the operator can perform the following with synthetic or approved customer data:

1. configure the customer environment
2. validate config and readiness
3. create bootstrap tenant or session state
4. import approved source records
5. score and prioritize accounts
6. request approval before an outbound action
7. execute an approved send through the safe channel
8. receive or ingest webhook outcome results
9. verify audit record creation
10. confirm the system remains consistent after backup/restore rehearsal

## Operations

The pilot must support:

- logs inspection for API and dependent services
- service restarts without hidden data loss
- backup of Postgres data
- restore testing in an isolated environment
- operator signoff for customer launch
- documented escalation path for failed sends or webhook issues

## Acceptance tests

This is the minimal acceptance suite that must pass before signoff:

```bash
python -m pytest -q
python scripts/validate_customer_config.py --env-file deploy/customer.env.example --check-public-demo
python scripts/validate_customer_config.py --env-file .env --production
python scripts/verify_deployment.py
```

Expected result: all checks pass, and the deployment verifier returns a `passed` status.

## Sign-off rule

The pilot is accepted only if:

- tests pass
- deployment verifier passes
- config validation passes with production requirements applied
- backup/restore rehearsal passes
- operator runbook is complete
- customer handover is complete
- product claims match actual scope

This is the standard for a real $4,500 founder pilot.
