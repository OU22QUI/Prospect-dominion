# Prospect Dominion

This workspace contains the Prospect Dominion design set and a minimal runnable starter scaffold for the sovereign infrastructure described in the documents.

## What's included

- `docker-compose.yml` with the core data, intelligence, orchestration, and optional overlays
- `docker-compose.comms.yml` and `docker-compose.observability.yml`
- Minimal FastAPI services for the API, OSINT worker, and supporting workers
- Local environment template at `.env.example`

## Quickstart

1. Copy `.env.example` to `.env` and fill in secrets.
2. Start data services:
   ```bash
   docker compose --profile data --profile observability up -d
   ```
3. Start the core stack:
   ```bash
   docker compose --profile core up -d
   ```
4. Start the intelligence tier:
   ```bash
   docker compose --profile intel up -d
   ```
5. Start the comms overlay when ready:
   ```bash
   docker compose --profile comms up -d
   ```

## Health checks

- API: http://localhost/health
- OSINT: http://localhost:8080/health
- Qdrant: http://localhost:6333/readyz

## Notes

This is a working scaffold derived from the docs, not a full production implementation of every workflow. It gives you a concrete base to extend from.
