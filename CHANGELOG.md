# Changelog

## v0.2.0

### Added

- Postgres-backed pilot API with tenant-scoped authentication and authorization.
- CSV signal import, deterministic prioritisation, human approvals, outcome tracking, and audit history.
- Integration tests for the governed workflow, tenant isolation, and webhook tenant binding.
- Operator and deployment documentation for a controlled single-customer pilot.

### Changed

- Public site now focuses on the proposed CSV-backed outbound workflow and clearly separates the MIT core from scoped Aethonex services.
- Partner and post-pilot packages are marked as deferred; unsupported integration and ownership claims were removed.
- Public-demo audit now verifies external scheduling/privacy disclosures and rejects first-party forms pending privacy review.

### Readiness

This is a self-hosted pilot foundation, not a hosted multi-tenant SaaS product. Customer use still requires environment-specific technical and security review, approved data processing terms, provider setup, and written acceptance criteria.

## v0.1.0

Initial public release of the Prospect Dominion core.

### Included

- open-source core workflow foundation
- local pilot deployment path
- Postgres-backed operational state
- documentation for quickstart, deployment, and pilot use
- validation scripts for configuration and deployment readiness
- public demo experience for evaluation

### Not included

- broad multi-tenant SaaS architecture
- subscription or billing system
- enterprise procurement automation
- broad autonomous AI control plane

### Scope

This release is a usable open-source core and a bounded pilot-ready foundation, not a universal enterprise platform.
