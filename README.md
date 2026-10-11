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

The Core is MIT-licensed and remains useful, self-hostable, and redistributable without buying anything from Aethonex. The current paid path is a scoped implementation engagement around that Core—not a proprietary edition or a license fee for access to the same code.

Customers pay for agreed delivery work such as customer-environment setup, a bounded workflow implementation, agreed integrations and governance configuration, validation, documentation, and handover. Scope, price, support, and customer rights must be stated in a written agreement.

No paid Dominion software edition or proprietary module is currently shipped, and no standard price is published. See [the commercial offer definition](docs/COMMERCIAL_OFFER.md) for scope boundaries and acceptance expectations.

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

## Commercial path

The paid path is a scoped implementation engagement around the MIT Core, not a separate paid edition. The initial scope and acceptance expectations are documented in [docs/COMMERCIAL_OFFER.md](docs/COMMERCIAL_OFFER.md). Any delivery remains subject to customer-specific security, deployment, and written commercial terms.

## Quickstart

```bash
git clone https://github.com/OU22QUI/Prospect-dominion.git
cd Prospect-dominion
cp deploy/customer.env.example .env
python scripts/validate_customer_config.py --env-file .env --check-public-demo
python -m pytest -q
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile pilot up -d --build --wait
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
- [docs/COMMERCIAL_OFFER.md](docs/COMMERCIAL_OFFER.md)
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

## Relationship to other Aethonex projects

Prospect Dominion is an independent open-source project. Its current pilot imports customer-provided CSV data and supports a Resend-backed send path; it does not currently ingest Prospect Intelligence OS `dossier_v1` files. Other Aethonex products are not bundled with or integrated into this repository.

## Project status

See [docs/PRODUCT_STATUS.md](docs/PRODUCT_STATUS.md) for the verified scope and [docs/ROADMAP_GAPS.md](docs/ROADMAP_GAPS.md) for known limitations. This is a self-hosted core with a bounded pilot path, not a general-purpose multi-tenant SaaS service.

## Repository boundaries

- [Prospect Intelligence OS](https://github.com/OU22QUI/prospect-intelligence-os): Apache-2.0 public-data company research; emits the versioned `dossier_v1` JSON contract.
- Prospect Dominion: independent MIT-licensed governed signal-to-action API and pilot console. It does not currently consume `dossier_v1` or interoperate with other products as an integrated suite.

These are separate projects, not an integrated product suite. No broader product-suite integration or commercial production readiness is implied.
