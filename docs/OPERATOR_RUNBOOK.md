# Operator Runbook

## Overview

This runbook exists to help a real operator run a Prospect Dominion pilot without reverse-engineering the repository. It assumes one controlled customer deployment and a single workflow path.

## 1. Confirm deployment health

```bash
python scripts/verify_deployment.py
curl -H "Authorization: Bearer $PD_API_KEY" http://127.0.0.1:8010/ready
```

Required result:

- Deployment verifier returns `status: passed`
- `/ready` returns `status: ready`
- /health returns `status: ok`

## 2. Confirm operator access

Use the configured customer environment and log in with the approved operator account. Only operator-level or approved roles should be permitted to approve sends or modify workflow state.

## 3. Import or load data

Use the approved data import path. Do not import unsupported or unreviewed records. Validate provenance and idempotency before moving a record into active workflow state.

## 4. Review the queue

Inspect:

- account priority
- signal provenance
- score explanations
- suppression status
- current workflow stage

## 5. Approve and send

The operator should:

- select the approved account
- confirm the proposed action
- require approval before external send
- verify the recipient and send channel
- confirm the audit record is created

## 6. Monitor outcome

Track:

- send attempt status
- webhook outcome
- operator response
- audit events

## 7. Escalate failure

Escalate when:

- webhook validation fails
- the send path rejects an approved action
- workflow state becomes inconsistent
- the API or database is unhealthy

## 8. Backup and restore

See [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## 9. Restart sequence

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core restart
python scripts/verify_deployment.py
```

## 10. After action review

Review:

- action status
- account state
- workflow stages
- audit entries
- any operational anomalies

## 11. Shutdown

Use a controlled shutdown after signoff or maintenance:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core down --remove-orphans
```

## 12. Known boundary

This runbook supports a controlled pilot. It is not a general-purpose administrator system for a self-service multi-tenant SaaS product.
