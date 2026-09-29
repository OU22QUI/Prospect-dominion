# Production

This project is suitable for a controlled self-hosted or customer deployment model, but it is not a universal multi-tenant SaaS deployment.

Required production conditions:

- HTTPS public URL
- valid DNS and TLS
- non-placeholder secrets
- Postgres and Redis configured properly
- operator-managed approval process
- supported data ingestion path

See [docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md](docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md) for the exact deployment flow.
