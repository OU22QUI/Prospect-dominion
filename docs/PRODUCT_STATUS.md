# Product Status

## Current description

Prospect Dominion is an MIT-licensed, self-hostable software core with a local technical evaluation path and a public, static product simulation. The simulation uses seeded fictional data; it does not connect to customer systems or send external actions.

Deployment files and pilot documentation describe a candidate single-customer workflow. They are not evidence that a customer deployment has been completed or that a commercial service is production-ready.

## What repository checks can establish

Automated tests, configuration checks, and local smoke tests can establish that specific code paths work under the tested conditions. They do not establish customer adoption, security certification, production reliability, commercial outcomes, or suitability for a particular customer's environment. Consult the CI run and test output for the exact revision being evaluated.

## Not demonstrated by this repository

- a paying customer, customer deployment, or customer-validated outcome
- revenue impact, conversion lift, time savings, or other measured business results
- universal compatibility with third-party services or customer infrastructure
- multi-tenancy, self-serve provisioning, billing, or a managed SaaS service
- a validated or fixed commercial price

No public demo metric should be interpreted as a measured customer result.

## Customer deployment prerequisites

Before using customer data or deploying to a customer environment, scope and verify:

- public DNS, valid TLS, HTTPS hostname, and origin configuration
- customer-specific secrets and environment configuration
- data-processing terms, data flows, and approved subprocessors
- provider credentials and webhook configuration, where applicable
- approved data loads, operator access, and human-approval policy
- backup and restore in the target environment

See the [customer deployment runbook](CUSTOMER_DEPLOYMENT_RUNBOOK.md), [pilot acceptance criteria](PILOT_ACCEPTANCE.md), and [backup/restore procedure](BACKUP_RESTORE.md). A checklist is not a substitute for completing and documenting those steps for a specific deployment.

## Roadmap / not included

- multi-tenancy
- self-serve customer provisioning
- billing/subscription management
- generalized enterprise administration
- broad universal integration layer
- white-label infrastructure
- broad autonomous orchestration
