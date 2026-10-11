# Deployment

This is the public deployment guide for the open-source core and the bounded pilot environment.

## Local development

```bash
cp deploy/customer.env.example .env
python scripts/validate_customer_config.py --env-file .env --check-public-demo
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile pilot up -d --build --wait
python scripts/verify_deployment.py
```

By default, the deployment verifier is read-only and does not create demo or customer workflow records. Set `PD_PILOT_TOKEN` to a current pilot session token when you also want it to check authenticated read access to the versioned pilot API. The optional `--teardown` flag stops the pilot Compose stack and should not be used for customer deployments.

## Real customer deployment

Use the production configuration contract defined in [docs/PRODUCTION.md](PRODUCTION.md) and [docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md](docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md).

## Requirements

- public domain
- HTTPS certificate
- custom secrets
- approved workflow data
- operator ownership
