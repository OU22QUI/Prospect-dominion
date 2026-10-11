# Quickstart

## Prerequisites

- Docker Desktop or Docker Engine + Compose
- Python 3.11
- Git
- access to a local terminal

## 1. Clone and configure

```bash
git clone https://github.com/OU22QUI/Prospect-dominion.git
cd Prospect-dominion
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
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile pilot up -d --build --wait
```

Expected result: Postgres, the migration runner, API, and Caddy start. This is the lean single-workspace pilot profile; optional Redis, Qdrant, Neo4j, LiteLLM, and crawling services are not required.

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

### Docker startup issue

Inspect the pilot service status and logs first:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile pilot ps
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile pilot logs --tail=200
```

Do not remove Docker volumes as a routine troubleshooting step; the Postgres volume contains persistent workflow data.

### API not ready

Check the API logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile pilot logs --tail=200 api
```

### Config validation fails

Review `.env` entries and ensure placeholders are replaced for production.

## Production note

A real deployment still requires the external deployment setup described in [DEPLOYMENT.md](DEPLOYMENT.md).

The pilot does not require Redis or Qdrant. For a deployment that enables those optional services, set `PD_CHECK_REDIS=true` and/or `PD_CHECK_QDRANT=true` to include them in production readiness checks. Sending through the pilot currently requires customer-configured Resend credentials; provider pricing and free allowances are outside this repository and are not guaranteed.
