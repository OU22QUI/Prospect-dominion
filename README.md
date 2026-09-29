# Prospect Dominion

Prospect Dominion Core is open-source signal-to-action infrastructure for teams that want to run a governed workflow in their own environment.

The initial pilot focus is outbound and lead-generation agencies moving from customer-provided signal exports to prioritized accounts and human-approved actions. Broader connectors and operating models are not implied by this initial scope.

The core idea is simple:

signals
→ prioritize
→ route
→ approve
→ act
→ track

It is designed for real operator control and a human approval gate, not for unchecked autonomous outreach.

**Start here:** [Product site](https://dominion.aethonex.com/) · [Interactive simulation](https://dominion.aethonex.com/demo/) · [Self-hosting quickstart](docs/QUICKSTART.md) · [GitHub source](https://github.com/OU22QUI/Prospect-dominion)

## Open-source core, paid deployment path

The honest model is:

- open-source core: usable, self-hostable, and inspectable
- Aethonex deployment service: real environment setup, workflow implementation, integrations, support, and handover
- future premium modules: only where real customer demand justifies them

This repository is the public Core. The commercial value is in the implementation around it. We sell deployment, customization, and operational execution—not software access alone.

## Why use Dominion?

- run an accountable workflow instead of a black-box outbound system
- keep approvals and send decisions visible
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
- Aethonex deployment services: production setup, DNS/TLS, secret management, workflow implementation, support, and customer-specific configuration
- paid implementation path: one real workflow deployed in a real customer environment

See [docs/OPEN_SOURCE_CORE.md](docs/OPEN_SOURCE_CORE.md) and [docs/COMMERCIAL_BOUNDARY.md](docs/COMMERCIAL_BOUNDARY.md).

## Quickstart

```bash
git clone https://github.com/OU22QUI/Prospect-dominion.git
cd Prospect-dominion
cp deploy/customer.env.example .env
python scripts/validate_customer_config.py --env-file .env --check-public-demo
python -m pytest -q
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build --wait
python scripts/verify_deployment.py
```

Then browse:

- API readiness: http://127.0.0.1:8010/ready
- demo: http://127.0.0.1:8000

For prerequisites, troubleshooting, and the full verified setup path, see [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Demo

The [public product simulation](https://dominion.aethonex.com/demo/) is for product explanation and evaluation. It uses sample values and clearly represents a demonstration workspace. The simulation is not a live customer environment; use the Quickstart above to run the self-hosted core.

The same simulation is included in `demo/` for local use.

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

## Company and public links

- Website: https://aethonex.com
- LinkedIn: https://www.linkedin.com/company/aethonex
- X: https://x.com/aethonex

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Project status

See [docs/PRODUCT_STATUS.md](docs/PRODUCT_STATUS.md) for the verified scope and [docs/ROADMAP_GAPS.md](docs/ROADMAP_GAPS.md) for known limitations. This is a self-hosted core with a bounded pilot path, not a general-purpose multi-tenant SaaS service.

## Commercial model

Aethonex can provide deployment, configuration, workflow customization, operation, and support services around the open-source core. The pilot remains a bounded paid implementation for real customer environments, not a claim that every deployment problem is solved by the OSS layer alone.
