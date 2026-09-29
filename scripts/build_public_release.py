#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
ARCHIVE_NAME = f"Prospect-Dominion-Core-v{VERSION}.zip"
ARCHIVE_PATH = ROOT / ARCHIVE_NAME
MANIFEST_NAME = f"RELEASE_MANIFEST_v{VERSION}.txt"
MANIFEST_PATH = ROOT / MANIFEST_NAME
TAG_NAME = f"v{VERSION}"

ROOT_INCLUDE = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "THIRD_PARTY_NOTICES.md",
    "VERSION",
    "pytest.ini",
    "docker-compose.yml",
    "docker-compose.override.yml",
    "docker-compose.comms.yml",
    "docker-compose.observability.yml",
    "deploy/customer.env.example",
    "scripts/build_public_release.py",
    "scripts/validate_public_release.py",
    "scripts/validate_customer_config.py",
    "scripts/verify_deployment.py",
    "scripts/backup_restore_rehearsal.py",
    "services/api/app/main.py",
]

PUBLIC_DIRS = [
    "docs",
    "demo",
    "deploy",
    "infra",
    "migrations",
    "scripts",
    "services",
    "workflows",
    "data",
]

PRIVATE_ROOT_MARKERS = {
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
    "RELEASE-CANDIDATE.md",
    "RELEASE-NOTES-v1.0.0-rc1.md",
    "TESTER-README.md",
    "Prospect Dominion — MLOps & Model Sovereignty Layer.md",
    "Prospect-Dominion-ABM-Buying-Committee-Layer.md",
    "Prospect-Dominion-ABM-Buying-Committee-Layer (1).md",
    "Prospect-Dominion-Data-Layer-Schemas (1).md",
    "Prospect-Dominion-Governance-Trust-Control-Plane.md",
    "Prospect-Dominion-Governance-Trust-Control-Plane (1).md",
    "Prospect-Dominion-Rep-Cockpit-HITL-Layer.md",
    "Prospect-Dominion-Rep-Cockpit-HITL-Layer (1).md",
    "Prospect-Dominion-W2-Enrichment-EmailHunt-Workflow (1).md",
    "Prospect-Dominion-W5-Conversation-Loop-Workflow (1).md",
    "Prospect-Dominion-WG2-Signal-First-Workflow (1).md",
    "Prospect-Dominion-WL1-Outcome-Ingest-Workflow (1).md",
    "Prospect-Dominion-WL2-6-Learning-Flywheel-Workflow (1).md",
    "Prospect-Dominion-WO1-Touch-Dispatcher-Workflow (1).md",
    "Prospect-Dominion-WV-Readiness-Booking-Workflow (1).md",
    "Prospect-Dominion-Warm-Intro-Relationship-Graph-Layer.md",
    "Prospect-Dominion-Workflow-Suite-Index (1).md",
    "Prospect-Dominion-Competitive-Market-Intelligence-Layer.md",
    "Prospect-Dominion-Deployment-Runbook.md",
    "Prospect-Dominion-Deployment-Offer.md",
    "Prospect-Dominion-Demo-Script.md",
    "Prospect-Dominion-Executive-Handoff.md",
    "Prospect-Dominion-Infra-Scaffold (1).md",
    "Prospect-Dominion-Product-Brief.md",
    "Prospect-Dominion-Pilot-Overview.md",
    "Prospect-Dominion-Commercial-Playbook.md",
    "Prospect-Dominion-Pricing-Overview.md",
    "Prospect-Dominion-White-Label-Offer.md",
    "Prospect-Dominion-Slide-Deck-Summary.md",
    "Prospect-Dominion-Sales-Assets.md",
    "Prospect-Dominion-Customer-One-Pager.md",
    "Prospect-Dominion-Customer-Deployment.md",
}

FORBIDDEN_PATTERNS = (
    ".git",
    ".env",
    ".pytest_cache",
    "__pycache__",
    "prospect-dominion-backup.dump",
    ".DS_Store",
    ".idea",
)

REQUIRED_FILE_SET = {
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


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, check=check)


def should_exclude(rel_path: str) -> bool:
    rel_lower = rel_path.lower()
    if rel_path in PRIVATE_ROOT_MARKERS:
        return True
    for marker in FORBIDDEN_PATTERNS:
        if marker in rel_lower:
            return True
    if rel_path.startswith("."):
        return True
    if rel_path.startswith(".git/"):
        return True
    if rel_path.startswith(".github/"):
        return True
    if rel_path.endswith((".pyc", ".pyo", ".log", ".dump", ".sqlite", ".sqlite3", ".db")):
        return True
    if "__pycache__" in rel_path:
        return True
    if rel_path.startswith("data/") and rel_path.endswith(":Zone.Identifier"):
        return True
    if rel_path.startswith(".pytest_cache/"):
        return True
    return False


def public_files() -> list[str]:
    files: set[str] = set()

    for rel in ROOT_INCLUDE:
        p = ROOT / rel
        if p.exists():
            files.add(rel)

    for rel_dir in PUBLIC_DIRS:
        p = ROOT / rel_dir
        if not p.exists():
            continue
        for child in sorted(p.rglob("*"), key=lambda x: x.relative_to(ROOT).as_posix()):
            if child.is_dir():
                continue
            rel = child.relative_to(ROOT).as_posix()
            if should_exclude(rel):
                continue
            files.add(rel)

    # Ensure release builder and validation scripts are included even if not under a public dir.
    for rel in ["scripts/build_public_release.py", "scripts/validate_public_release.py"]:
        if (ROOT / rel).exists():
            files.add(rel)

    # Exclude generated archive or manifest from the archive itself.
    files.discard(ARCHIVE_NAME)
    files.discard(MANIFEST_NAME)
    return sorted(files)


def make_zip(file_list: list[str]) -> None:
    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()

    with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in file_list:
            src = ROOT / rel
            if not src.exists():
                raise FileNotFoundError(f"Required file missing in release set: {rel}")
            data = src.read_bytes()
            info = zipfile.ZipInfo(rel)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.comment = b""
            info.create_system = 3
            zf.writestr(info, data)


def generate_manifest(file_list: list[str]) -> None:
    commit = "unknown"
    try:
        result = run(["git", "rev-parse", "HEAD"])
        commit = result.stdout.strip() or commit
    except Exception:
        pass

    lines = [
        f"Prospect Dominion Core Release {VERSION}",
        f"Archive: {ARCHIVE_NAME}",
        f"Tag: {TAG_NAME}",
        f"Commit: {commit}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Files:",
    ]
    for rel in file_list:
        src = ROOT / rel
        size = src.stat().st_size
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        lines.append(f"{rel}\t{size}\t{sha}")
    MANIFEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_checksum() -> str:
    h = hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest()
    checksum_path = ARCHIVE_PATH.with_suffix(".zip.sha256")
    checksum_path.write_text(f"{h}  {ARCHIVE_NAME}\n", encoding="utf-8")
    return h


def validate_required_files(file_list: list[str]) -> None:
    missing = sorted(set(REQUIRED_FILE_SET) - set(file_list))
    if missing:
        raise SystemExit(f"Missing required release files: {missing}")


def main() -> int:
    file_list = public_files()
    validate_required_files(file_list)
    make_zip(file_list)
    generate_manifest(file_list)
    sha = write_checksum()
    print(f"Release created: {ARCHIVE_PATH}")
    print(f"Manifest created: {MANIFEST_PATH}")
    print(f"SHA256: {sha}")
    print(f"Included files: {len(file_list)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        print(f"Release build failed: {exc}", file=sys.stderr)
        sys.exit(1)
