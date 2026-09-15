# Prospect Dominion Tester Path

## Public demo

The public demo is a static, credential-free showcase. It does not call the private API and does not require Docker.

```text
https://<github-owner>.github.io/<repository>/
```

The repository publishes `demo/` through GitHub Pages using `.github/workflows/publish-demo.yml`.

## What to test

1. Open the demo on desktop and mobile widths.
2. Use the `View workflow` action and confirm it scrolls to the workflow panel.
3. Use `Request technical walkthrough` and confirm the technical-demo panel appears.
4. Review the account table, signal states, trust controls, and workflow progression.
5. Confirm there are no credentials, private URLs, or internal service references in the page source.

## Technical demo

The technical demo runs locally from the repository root:

```powershell
Copy-Item deploy/customer.env.example .env
python scripts/validate_customer_config.py --env-file .env --check-public-demo
docker compose -f docker-compose.yml -f docker-compose.override.yml --profile core up -d --build
$env:PD_API_KEY="dev-local-key"
$env:PD_BASE_URL="http://127.0.0.1:8010"
python scripts/verify_deployment.py
```

The technical demo verifies readiness, authentication, branding, seeded data, and workflow advancement. It is separate from the public static demo.

## Report a problem

Include:

- public or technical demo
- browser and viewport
- exact action taken
- expected result
- observed result
- screenshot or console error when relevant

Do not include API keys, customer data, or `.env` contents in a report.
