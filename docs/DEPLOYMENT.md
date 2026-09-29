# Deployment

This is the public deployment guide for the open-source core and the bounded pilot environment.

## Local development

```bash
cp deploy/customer.env.example .env
python scripts/validate_customer_config.py --env-file .env --check-public-demo
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build --wait
python scripts/verify_deployment.py
```

## Real customer deployment

Use the production configuration contract defined in [docs/PRODUCTION.md](PRODUCTION.md) and [docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md](docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md).

## Requirements

- public domain
- HTTPS certificate
- custom secrets
- approved workflow data
- operator ownership
