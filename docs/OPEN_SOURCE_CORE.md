# Open Source Core

## What is in the Core

The current open-source core contains the parts that have already been verified and that are genuinely useful to run in a local or self-hosted environment:

- FastAPI application
- Postgres-backed pilot state
- validation scripts
- deployment verification scripts
- demo experience
- configuration and deployment documentation
- operator and pilot guidance

## What the Core is designed to do

The open-source core supports a governed signal-to-action workflow for a single environment and a bounded pilot.

It provides:

- signal intake and normalization
- workflow state tracking
- approval gate enforcement
- audit records
- send and webhook safety checks
- local deployment and validation

## What the Core is not

The Core is not a universal SaaS platform, a multi-tenant cloud control plane, or a broad autonomous AI product. It does not include a complete billing, subscriptions, or enterprise procurement surface.

## Why this is legitimate open source

It is useful, runnable, and testable without requiring a paid deployment. It acts as a deployable developer core and creates a path to Aethonex deployment and custom implementation services.

## Portfolio boundary

Prospect Dominion is an independent MIT-licensed workflow project. Its current pilot ingests CSV signals and does not consume the `dossier_v1` contract from Prospect Intelligence OS. Treat those as separate products until a versioned adapter and end-to-end integration test exist.

## Commercial boundary

The Core remains available under the MIT License, including for commercial use and redistribution. The current paid path is implementation work around the Core: scoped environment deployment, workflow configuration, agreed integrations, validation, documentation, and handover. There is no separate paid Dominion edition or proprietary Dominion module shipped today.

Any paid engagement must define its delivery scope, acceptance checks, customer rights, support, and price in a written agreement. See [Commercial Offer](COMMERCIAL_OFFER.md) and [Commercial Boundary](COMMERCIAL_BOUNDARY.md).
