# Prospect Dominion API

This API provides the core operational surface for the Prospect Dominion platform.

## Endpoints

- `GET /health`
- `GET /ready`
- `GET /branding`
- `GET /`
- `GET /dashboard`
- `GET /orchestration/{thread_id}`
- `GET /threads`
- `POST /threads`
- `GET /accounts`
- `POST /accounts`
- `GET /people`
- `POST /people`
- `GET /events`
- `POST /events`
- `GET /outcomes`
- `POST /outcomes`

## Run locally

```bash
cd services/api
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

For a Compose deployment, run the repository-level verifier from the project root:

```bash
python scripts/verify_deployment.py
```
