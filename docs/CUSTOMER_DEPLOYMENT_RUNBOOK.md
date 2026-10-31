# Customer Deployment Runbook

## Scope

This runbook describes the deterministic deployment path for a single Prospect Dominion pilot. It is intentionally narrow and does not assume multi-tenant SaaS operations.

## 1. Provision the host

Use a dedicated Linux or Docker-capable host with:

- Docker Engine and Docker Compose
- Python 3.11 available for validation scripts
- outbound HTTPS for Resend and the public base URL
- protected access for ports 80 and 443 only
- a managed firewall that does not expose Postgres or Redis publicly

## 2. Configure DNS

Create the hostname record mapped to the public host. Example:

```text
pilot.customer.example  A  <host-ip>
```

Configure the reverse proxy or Caddy host to terminate TLS and proxy to the API service.

## 3. Configure HTTPS/TLS

Set the production public URL to the final customer hostname.

Example:

```env
APP_ENV=production
PUBLIC_BASE_URL=https://pilot.customer.example
PD_PUBLIC_HOST=pilot.customer.example
PD_CADDYFILE=./infra/caddy/Caddyfile.production
```

Verify that the hostname resolves and the HTTPS certificate can be obtained before importing customer data.

## 4. Create a customer environment file

```bash
cp deploy/customer.env.example .env
```

Update the values below:

```env
APP_ENV=production
PUBLIC_BASE_URL=https://pilot.customer.example
PD_PUBLIC_HOST=pilot.customer.example
PD_CADDYFILE=./infra/caddy/Caddyfile.production
PD_BRAND_NAME=Customer Brand
PD_BRAND_TAGLINE=Signal-to-action pilot
PD_PRIMARY_COLOR=#4f8ef7
PD_API_KEY=prod-<generated>
PD_DEFAULT_ROLE=viewer
JWT_SECRET=<32+ chars>
PG_USER=aethonex
PG_PASSWORD=<strong password>
PG_DB=prospect_dominion
REDIS_PASSWORD=<strong password>
RESEND_API_KEY=re_<generated>
RESEND_WEBHOOK_SECRET=whsec_<generated>
```

Do not keep placeholder values or local development secrets in the customer environment.

## 5. Validate the environment

Run:

```bash
python scripts/validate_customer_config.py --env-file .env --production --check-public-demo
```

Expected result: JSON output with `"status": "valid"` and no production validation errors.

## 6. Start the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build --wait
```

Expected result: the Postgres, migrations, API, Caddy, and required core services start successfully.

## 7. Verify readiness

```bash
python scripts/verify_deployment.py
```

Expected result: a JSON payload with `"status": "passed"`.

## 8. Bootstrap the pilot

Create or initialize the pilot admin/operator state only after readiness passes.

Use the customer-authenticated route or internal bootstrap process defined by the running deployment. Keep the bootstrap record in a controlled, auditable environment.

## 9. Load approved pilot data

Load only approved synthetic or controlled customer data. Do not run real outbound sends before verifying the workflow in a safe environment.

## 10. Validate workflow sequence

Expected workflow checks:

- ingest approved signals
- score and rank accounts
- request approval for a send
- reject disallowed or suppressed cases
- send only after approval
- capture webhook or outcome result
- record the audit trail

## 11. Validate approval and send safety

Verify the following:

- suppressed recipients are rejected
- invalid workflow state transitions fail
- unauthorized roles cannot perform writes
- approved send attempts record audit details
- webhook payload verification is enforced

## 12. Validate outcome path

Test that a signed webhook or provider callback updates the action record and marks the outcome correctly.

## 13. Backup and restore rehearsal

Use the backup/restore procedure in [BACKUP_RESTORE.md](BACKUP_RESTORE.md). This must be tested before calling the pilot operationally ready.

## 14. Sign-off

The deployment is accepted only when:

- config validation passes
- readiness checks pass
- deployment verifier returns passed
- backup/restore rehearsal passes
- send and approval safety pass
- operator handoff is documented

## Operational boundaries

This deployment is not a multi-tenant operating model. It is designed for one customer at a time and should be treated as a controlled pilot environment until a separate engagement expands the product scope.
