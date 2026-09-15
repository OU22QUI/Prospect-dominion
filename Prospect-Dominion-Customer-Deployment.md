# Prospect Dominion Customer Deployment

## Purpose

This package defines the repeatable pilot deployment path for one customer environment. It uses configuration rather than source-code forks and supports environment-level branding.

This is a single-customer deployment model. It is not a multi-tenant SaaS control plane.

## Deployment modes

### Local pilot

- `APP_ENV=local`
- local Docker Compose stack
- seeded demo data
- development credentials replaced before customer access

### Customer production environment

- `APP_ENV=production`
- customer-owned host or cloud environment
- production API key with `prod-` prefix
- HTTPS public URL
- generated database, JWT, Redis, and workflow secrets
- customer-specific branding values

## 1. Prepare configuration

```powershell
Copy-Item deploy/customer.env.example .env
```

Set customer values in `.env`:

- `PD_BRAND_NAME`
- `PD_BRAND_TAGLINE`
- `PD_PRIMARY_COLOR`
- `PUBLIC_BASE_URL`
- credentials and service secrets
- host ports appropriate for the environment

For a customer deployment, do not leave placeholder values such as `change-me`, `dev-local-key`, or `sk-local-change-me`.

## 2. Validate configuration

Pilot validation:

```powershell
python scripts/validate_customer_config.py --env-file .env --check-public-demo
```

Production validation:

```powershell
python scripts/validate_customer_config.py --env-file .env --production --check-public-demo
```

The validator reports machine-readable JSON and never prints secret values.

## 3. Start the deployment

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build
```

## 4. Verify the deployment

```powershell
$env:PD_API_KEY = "<the configured API key>"
$env:PD_BASE_URL = "http://127.0.0.1:8010"
python scripts/verify_deployment.py
```

For an HTTPS customer URL, set `PD_BASE_URL` to that URL instead.

## 5. Initialize a pilot

The deployment verifier seeds a safe demonstration record and exercises a workflow transition. For a real customer environment, replace seeded data with an approved customer initialization process before importing production records.

The current application stores local operational records in SQLite. Treat the pilot database as deployment data and include it in the customer's backup and retention plan.

## 6. Operate and update

Before an update:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core ps
python scripts/verify_deployment.py
```

After an update, rerun the same verifier. Keep the customer `.env` outside source control and preserve the configured secrets during rebuilds.

To stop the environment cleanly:

```powershell
python scripts/verify_deployment.py --teardown
```

## Current boundaries

Implemented:

- environment-level branding
- production configuration validation
- protected API routes
- readiness and health checks
- repeatable Compose startup
- machine-checkable deployment verification

Not included in this deployment package:

- multiple tenants in one runtime
- customer user invitations
- billing
- automated backups
- remote infrastructure provisioning
- customer-specific workflow administration UI

Those are separate product maturity phases and should be built only when a paying deployment requires them.
