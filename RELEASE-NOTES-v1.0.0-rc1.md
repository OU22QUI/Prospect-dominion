# Prospect Dominion v1.0.0-rc1

## Release status

Release candidate for public demonstration, independent testing, white-label pilots, and controlled customer deployment.

## Included

- FastAPI application with authenticated operational routes
- SQLite operational persistence for pilot deployments
- Workflow progression, orchestration, dashboard, events, and outcomes
- Production configuration validation and masked secret output
- Environment-level white-label branding
- Hardened Docker Compose deployment
- Deterministic deployment verifier
- Customer deployment template and validator
- Credential-free static public demo
- Self-contained tester page
- GitHub Pages publication workflow
- Public-demo secret and internal-endpoint scanning

## Verification evidence

- 20 application tests passed
- Compose configuration validated
- Full core Compose deployment reached healthy state
- Deployment verifier passed health, readiness, auth, branding, seed, and workflow checks
- Customer configuration validator passed
- Public demo served homepage, tester page, CSS, and JavaScript over HTTP 200
- Public demo safety scan passed
- Python compilation and static diagnostics passed
- Clean Compose teardown passed

## Release boundary

This release is not a claim of multi-tenant SaaS readiness. Customer environments are currently deployed as isolated, environment-level instances. User administration, billing, managed provisioning, automated backups, and customer workflow administration remain later product phases.

## Publication status

The GitHub Pages workflow is complete, but this workspace has no configured Git remote. The release becomes publicly accessible after a GitHub repository is created, `main` is pushed, and Pages is enabled using GitHub Actions.