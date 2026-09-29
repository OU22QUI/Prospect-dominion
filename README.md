# Prospect Dominion

Prospect Dominion is open-source signal-to-action infrastructure for teams that want to run a governed GTM workflow in their own environment.

The core idea is simple:

signals
→ prioritize
→ route
→ approve
→ act
→ track

It is designed for real operator control and human approval gates, not for unchecked autonomous outreach.

## Why use Dominion?

- run an accountable workflow instead of a black-box outbound system
- keep workflow approvals and send decisions visible
- normalize signals into a shared operating model
- track outcomes and audit actions
- self-host the core in your environment

## What is included

- FastAPI-based workflow service
- Postgres-backed storage for pilot-grade operational state
- demo and static product experience for evaluation
- validation and deployment scripts
- service dockerization for a local pilot path

## What is not included

This repository is not a generic multi-tenant cloud product. It is a self-hosted core plus a bounded pilot/deployment path designed to be extended by real operators and deployment partners.

## Open-source core and commercial path

Prospect Dominion intentionally separates:

- open-source core: usable and self-hostable
- Aethonex deployment services: production setup, DNS/TLS, secret management, workflow implementation, support
- future premium modules: advanced workflow packs and enterprise-specific additions

See [docs/OPEN_SOURCE_CORE.md](docs/OPEN_SOURCE_CORE.md) and [docs/COMMERCIAL_BOUNDARY.md](docs/COMMERCIAL_BOUNDARY.md).

## Quickstart

```bash
cp deploy/customer.env.example .env
python scripts/validate_customer_config.py --env-file .env --check-public-demo
python -m pytest -q
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build --wait
python scripts/verify_deployment.py
```

Then browse:

- API readiness: http://127.0.0.1:8010/ready
- demo: http://127.0.0.1:8000

For full setup steps, see [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Demo

The public demo is a simulation for product explanation and evaluation. It uses sample values and clearly represents a demonstration workspace.

It should not be mistaken for a live customer environment.

## Documentation

- [docs/QUICKSTART.md](docs/QUICKSTART.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/PRODUCTION.md](docs/PRODUCTION.md)
- [docs/PILOT.md](docs/PILOT.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/OPEN_SOURCE_CORE.md](docs/OPEN_SOURCE_CORE.md)
- [docs/COMMERCIAL_BOUNDARY.md](docs/COMMERCIAL_BOUNDARY.md)
- [docs/PRODUCT_STATUS.md](docs/PRODUCT_STATUS.md)
- [docs/ROADMAP_GAPS.md](docs/ROADMAP_GAPS.md)
- [docs/AETHONEX_PILOT.md](docs/AETHONEX_PILOT.md)

## Security and contribution

- [SECURITY.md](SECURITY.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CHANGELOG.md](CHANGELOG.md)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Commercial model

Aethonex can provide deployment, configuration, workflow customization, operation, and support services around the open-source core. The pilot remains a bounded paid implementation for real customer environments, not a claim that every deployment problem is solved by the OSS layer alone.
