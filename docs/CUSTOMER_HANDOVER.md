# Customer Handover

## Purpose

This document explains the ownership boundary between Aethonex and the customer for the pilot deployment. It defines the operational and documentation responsibilities of each party at the point of handoff.

## What Aethonex provides

- repository and deployment configuration
- Compose deployment path and health verification
- seeded production-safe config validation
- operator and deployment documentation
- pilot deployment guidance and runtime checks
- guided migration from pilot to controlled customer environment

## What the customer owns

- public DNS and TLS host management
- final environment secrets and rotation policy
- final brand and public hostname configuration
- operational access management
- business workflow decisions and approval rules
- data retention and policy decisions
- provider account and webhook configuration outside the repo

## What is not included

The current deployment does not include broad enterprise provisioning, multi-tenant self-service management, subscription billing, or universal integrations. Those remain separate scopes and should be explicitly included in a future engagement.

## Handover requirements

Before customer signoff, the operator should confirm:

- the environment is healthy
- verification has been run successfully
- backup has been rehearsed
- restore is documented
- operator access is defined
- the customer knows which secrets they own
- the public hostname is validated and cert is live

## Transfer of operation

The operation can be transferred by documenting:

- host owner
- DNS owner
- secret owner
- monitoring ownership
- support escalation path
- backup retention path
- rollback procedure

A final pilot signoff must record the owner of each operational component and the agreed review cadence.
