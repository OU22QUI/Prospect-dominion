# Prospect Dominion — Demo Script

## Objective
This is a short, credible demo flow designed to show Prospect Dominion as a deployable, trust-aware AI revenue operations layer. The goal is to demonstrate that the system is not just conceptual; it is operational, protected, and healthy.

---

## Prerequisites
- Docker is running
- repo is open in the workspace
- Python 3.11 is available
- local environment defaults are active

Recommended local environment values:
- `API_PORT=8010`
- `OSINT_PORT=8081`
- `REDIS_PORT=6380`
- `PD_PORT=8010`
- `PD_API_KEY=dev-local-key`

---

## Step 1: Start the stack
From the repo root:

```powershell
cd "C:\Users\pc\Desktop\THE PROSPECT DOMINION"
$env:API_PORT="8010"
$env:OSINT_PORT="8081"
$env:REDIS_PORT="6380"
$env:PD_PORT="8010"
$env:PD_API_KEY="dev-local-key"
docker compose --profile core down --remove-orphans
docker compose --profile core up -d --build
```

Then confirm services:

```powershell
docker compose --profile core ps --format 'table {{.Service}}\t{{.State}}\t{{.Ports}}'
```

Narration:
> "The stack starts cleanly with non-conflicting local ports, which matters because a lot of demo environments fail on port collisions before the product even gets a chance to show value."

---

## Step 2: Check readiness
Run:

```powershell
python -c "import json, urllib.request; req=urllib.request.Request('http://127.0.0.1:8010/ready', headers={'Authorization':'Bearer dev-local-key'}); print(urllib.request.urlopen(req, timeout=10).status)"
```

Expected result:
- `200`

Narration:
> "The system exposes a real readiness contract. For a buyer, that means we know the stack is operational and not silently failing in the background."

---

## Step 3: Show the protected dashboard
Run:

```powershell
python -c "import json, urllib.request; req=urllib.request.Request('http://127.0.0.1:8010/dashboard', headers={'Authorization':'Bearer dev-local-key'}); body=urllib.request.urlopen(req, timeout=10).read().decode(); data=json.loads(body); print(sorted(data.keys())); print(data.get('thread_count')); print(data.get('project'))"
```

Expected result:
- valid JSON payload
- keys such as `event_count`, `outcome_count`, `recent_outcomes`, `thread_count`, `threads`

Narration:
> "This is the operational dashboard. It gives the team a visible operating surface, which is critical when you want AI workflows to be trusted rather than mysterious."

---

## Step 4: Explain the trust model
Try an unauthenticated call:

```powershell
python -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8010/dashboard');
try:
    print(urllib.request.urlopen(req, timeout=10).status)
except Exception as e:
    print(type(e).__name__)
    print(getattr(e, 'code', None))"
```

Expected result:
- `401` or `HTTPError` indicating protected access

Narration:
> "This is intentional. The platform is designed to fail safely: protected operational routes require a valid bearer token, which is how you build trust into AI systems instead of letting them run unguarded."

---

## Step 5: Explain the product value
Say:
> "Prospect Dominion is not just a list of data sources. It is a governed operating layer for revenue intelligence. It helps teams convert fragmented signal into coordinated action while preserving relationship context and operational trust."

Then highlight the main customer value points:
- account and relationship visibility
- workflow orchestration
- AI-assisted execution under explicit guardrails
- operational health and readiness visibility
- trust-first security posture

---

## Step 6: Close the demo
Final line:
> "The point is simple: Prospect Dominion gives revenue teams an AI operating layer that is visible, governable, and deployable. It is built not just to impress, but to be trusted in real execution."

---

## Confidence cues for the audience
Use these points to anchor the demo:
- local ports are stable and non-conflicting,
- the stack is healthy and ready,
- the dashboard is real and operational,
- the auth layer is secure,
- the runtime is fail-closed when misconfigured,
- and the system is positioned for real GTM execution rather than just concept display.

---

## Reference checks
The latest verification commands are:

```powershell
cd "C:\Users\pc\Desktop\THE PROSPECT DOMINION\services\api"
python -m pytest -q tests/test_api.py tests/test_dashboard.py tests/test_orchestration.py
```

Result:
- `15 passed in 1.14s`

```powershell
python -c "import json, urllib.request; req=urllib.request.Request('http://127.0.0.1:8010/ready', headers={'Authorization':'Bearer dev-local-key'}); print('ready_status', urllib.request.urlopen(req, timeout=10).status); req2=urllib.request.Request('http://127.0.0.1:8010/dashboard', headers={'Authorization':'Bearer dev-local-key'}); body=urllib.request.urlopen(req2, timeout=10).read().decode(); data=json.loads(body); print('dashboard_keys', sorted(data.keys())); print('thread_count', data.get('thread_count')); print('project', data.get('project'))"
```

Result:
- `ready_status 200`
- dashboard keys returned successfully
