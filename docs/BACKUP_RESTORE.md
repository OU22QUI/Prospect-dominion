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

A real pilot deployment is not accepted until a restore rehearsal has been successfully demonstrated on isolated data.

## Recovery notes

- Take backup before any customer-data migration or config change
- Keep encrypted backup copies outside the repository
- Record the timestamp and operator who executed the restore
- Perform restore testing before importing live customer data

## Known limitation

This is a single-customer pilot backup flow, not a fully managed enterprise backup platform.
