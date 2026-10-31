# Backup and Restore

## Purpose

This procedure covers the controlled backup and restore of the Postgres-backed pilot system. It is required before customer data is imported into a production pilot environment.

## Backup procedure

From the repository root:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core exec -T postgres pg_dump -U "$PG_USER" -Fc "$PG_DB" > prospect-dominion-backup.dump
```

Recommended follow-up:

```bash
gzip -c prospect-dominion-backup.dump > prospect-dominion-backup.dump.gz
```

Store the encrypted or protected file according to the customer retention policy.

## Restore procedure

To restore into a test or controlled environment:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core exec -T postgres pg_restore -U "$PG_USER" -d "$PG_DB" --clean --if-exists < prospect-dominion-backup.dump
```

After restore, validate:

```bash
python scripts/verify_deployment.py
```

Then confirm:

- API readiness remains healthy
- customer workflow records remain intact
- approved sends remain auditable
- webhook and outcome records remain consistent

## Operational requirement

A local isolated-data rehearsal passed on 2026-09-29 using `python scripts/backup_restore_rehearsal.py`: 24 source tables and 11 total rows matched the restored database, and the API readiness check remained healthy.

This verifies the local dump/restore path only. It does not satisfy the gate for a customer deployment. Before customer data is imported, repeat the rehearsal in that customer's deployment using isolated customer-specific data, record the operator, timestamp, and result, and confirm critical workflow and audit records. Backup protection, retention, and recovery targets must also be agreed for that environment.

## Recovery notes

- Take backup before any customer-data migration or config change
- Keep encrypted backup copies outside the repository
- Record the timestamp and operator who executed the restore
- Perform restore testing before importing live customer data

## Known limitation

This is a single-customer pilot backup flow, not a fully managed enterprise backup platform.
