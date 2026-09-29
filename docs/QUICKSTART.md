# Quickstart

## Prerequisites

- Docker Desktop or Docker Engine + Compose
- Python 3.11
- Git
- access to a local terminal

## 1. Clone and configure

```bash
git clone <repo-url>
cd Prospect-Dominion
cp deploy/customer.env.example .env
```

Update `.env` before running in a real environment.

## 2. Validate the configuration

```bash
python scripts/validate_customer_config.py --env-file .env --check-public-demo
```

Expected result: `"status": "valid"`.

## 3. Run tests

```bash
python -m pytest -q
```

Expected result: a passing suite.

## 4. Start the core stack

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build --wait
```

Expected result: Postgres, Redis, Qdrant, Neo4j, API, and related services start successfully.

## 5. Verify deployment

```bash
python scripts/verify_deployment.py
```

Expected result: JSON with `"status": "passed"`.

## 6. Open the demo

```bash
cd demo
python -m http.server 8000
```

Then open http://127.0.0.1:8000.

## 7. API readiness

```bash
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8010/ready', timeout=10).read().decode())"
```

Expected result: `status: ready`.

## Troubleshooting

### Docker network or stale volume issue

If you see a startup failure caused by stale Neo4j or Redis state, stop and remove stale volumes:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core down -v --remove-orphans
```

Then repeat the startup command.

### API not ready

Check the API logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core logs --tail=200 api
```

### Config validation fails

Review `.env` entries and ensure placeholders are replaced for production.

## Production note

A real deployment still requires the external deployment setup described in [DEPLOYMENT.md](DEPLOYMENT.md).
