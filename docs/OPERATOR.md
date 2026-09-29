# Operator Guide

The operator guide covers the day-to-day running of a bounded Prospect Dominion pilot.

## Core responsibilities

- validate service health
- confirm workflow state
- approve or reject sends
- check webhook outcome handling
- confirm audit records

## Health checks

```bash
python scripts/verify_deployment.py
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8010/ready', timeout=10).read().decode())"
```

## Backup and restore

See [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## Handover

See [CUSTOMER_HANDOVER.md](CUSTOMER_HANDOVER.md).
