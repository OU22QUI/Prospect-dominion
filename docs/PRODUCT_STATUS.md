# Product Status

## VERIFIED NOW

The following are currently proven by repository checks and runtime validation:

- full Python test suite passes
- public demo JavaScript syntax checks pass
- config validation passes for local/public demo checks
- Compose stack can render and run with the core profile
- API readiness and health checks pass
- deployment verifier reports a passing status
- the public demo renders and is commercially credible
- the single-customer pilot/deployment path is operational in a controlled environment

## REQUIRED PER CUSTOMER DEPLOYMENT

These items are operational requirements, not repository defaults:

- public DNS
- valid TLS certificate
- HTTPS hostname and origin configuration
- customer-specific environment file
- signed data-processing terms and an approved subprocessor list before customer-data use
- Resend API key and webhook secret
- JWT and database secrets
- approved data loads
- operator access and approval policy
- backup and restore rehearsal

## ROADMAP / NOT INCLUDED

The following remain outside the current pilot scope and are intentionally not implemented as part of this delivery:

- multi-tenancy
- self-serve customer provisioning
- billing/subscription management
- generalized enterprise administration
- broad universal integration layer
- white-label infrastructure
- broad autonomous orchestration
- speculative roadmap modules not required for one pilot workflow
