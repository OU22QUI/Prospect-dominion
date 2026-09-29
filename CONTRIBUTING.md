# Contributing

Thank you for helping improve Prospect Dominion.

## Development setup

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r services/api/requirements.txt
python -m pytest -q
```

## Pull request expectations

- keep changes small and testable
- add or update tests for behavioral changes
- document user-impacting changes
- avoid feature creep outside the current core scope

## Reporting issues

Open a GitHub issue with:

- what failed
- the command used
- what output you saw
- which environment you used
- whether the problem is local, deployment, or product scope

## Security disclosures

Do not open a public issue for a vulnerability. Follow the instructions in [SECURITY.md](SECURITY.md).
