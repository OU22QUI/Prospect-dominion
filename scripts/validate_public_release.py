#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
ARCHIVE_NAME = f"Prospect-Dominion-Core-v{VERSION}.zip"
REQUIRED_FILES = {
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/QUICKSTART.md",
    "docs/OPEN_SOURCE_CORE.md",
    "docs/COMMERCIAL_BOUNDARY.md",
    "docs/DEPLOYMENT.md",
    "docs/PRODUCTION.md",
    "docs/PILOT.md",
    "docs/OPERATOR.md",
    "docs/BACKUP_RESTORE.md",
    "docs/CUSTOMER_DEPLOYMENT_RUNBOOK.md",
    "docs/CUSTOMER_HANDOVER.md",
    "scripts/validate_customer_config.py",
    "scripts/verify_deployment.py",
    "scripts/backup_restore_rehearsal.py",
    "services/api/app/main.py",
    "docker-compose.yml",
    "docker-compose.override.yml",
    "deploy/customer.env.example",
    "demo/index.html",
}

FORBIDDEN_PREFIXES = (
    ".git",
    ".env",
    ".pytest_cache",
    "__pycache__",
    "prospect-dominion-backup.dump",
    "Prospect-Dominion-Commercial-Playbook.md",
    "Prospect-Dominion-Customer-Deployment.md",
    "Prospect-Dominion-Customer-One-Pager.md",
    "Prospect-Dominion-Deployment-Offer.md",
    "Prospect-Dominion-Deployment-Runbook.md",
    "Prospect-Dominion-Executive-Handoff.md",
    "Prospect-Dominion-Pilot-Overview.md",
    "Prospect-Dominion-Pricing-Overview.md",
    "Prospect-Dominion-Product-Brief.md",
    "Prospect-Dominion-Sales-Assets.md",
    "Prospect-Dominion-Slide-Deck-Summary.md",
    "Prospect-Dominion-White-Label-Offer.md",
    "Prospect-Dominion-Workflow-Suite-Index.md",
    "Prospect Dominion — MLOps & Model Sovereignty Layer.md",
    "RELEASE-CANDIDATE.md",
    "RELEASE-NOTES-v1.0.0-rc1.md",
    "TESTER-README.md",
)

FORBIDDEN_CONTENT_PATTERNS = (
    "BEGIN PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "AKIA",
    "AIza",
    "sk_live",
    "xoxb-",
    "xoxp-",
)

SECRET_LIKE_EXTENSIONS = (".pem", ".key", ".crt", ".p12", ".env", ".ini", ".conf")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the public release archive.")
    parser.add_argument("--archive", default=str(ROOT / ARCHIVE_NAME), help="Path to the release archive to validate.")
    return parser.parse_args()


def ensure_zip(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"Archive not found: {path}")
    names: list[str] = []
    with zipfile.ZipFile(path, 'r') as zf:
        names = zf.namelist()
        for name in names:
            if name.endswith('/'):
                continue
            if name.startswith("/"):
                raise SystemExit(f"Archive contains absolute path: {name}")
            if any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
                raise SystemExit(f"Archive contains forbidden public file: {name}")
            if name.startswith(".git/") or name.startswith(".github/"):
                raise SystemExit(f"Archive contains forbidden internal path: {name}")
            if name.startswith(".env") or ".env" in name:
                raise SystemExit(f"Archive contains env file: {name}")
            if name.endswith((".pyc", ".pyo", ".dump", ".sqlite", ".sqlite3", ".db")):
                raise SystemExit(f"Archive contains runtime artifact: {name}")
    return names


def check_required(names: list[str]) -> None:
    missing = sorted(REQUIRED_FILES - set(names))
    if missing:
        raise SystemExit(f"Archive missing required files: {missing}")


def check_secrets(archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('/'):
                continue
            lower_name = name.lower()
            if lower_name.endswith(".env.example"):
                continue
            if lower_name.endswith(("docker-compose.yml", "docker-compose.yaml", "docker-compose.override.yml", ".yml", ".yaml")):
                continue
            if not (
                lower_name.endswith(SECRET_LIKE_EXTENSIONS)
                or "secret" in lower_name
                or "credentials" in lower_name
            ):
                continue
            try:
                payload = zf.read(name).decode('utf-8', errors='ignore')
            except Exception:
                continue
            for marker in FORBIDDEN_CONTENT_PATTERNS:
                if marker in payload:
                    raise SystemExit(f"Archive contains secret-like marker {marker!r} in {name}")


def main() -> int:
    args = parse_args()
    archive_path = Path(args.archive).resolve()
    names = ensure_zip(archive_path)
    check_required(names)
    check_secrets(archive_path)
    print(f"Archive OK: {archive_path}")
    print(f"Files checked: {len(names)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        print(f"Validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
