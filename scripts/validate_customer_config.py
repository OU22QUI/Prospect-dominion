from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_KEYS = {
    "APP_ENV",
    "PUBLIC_BASE_URL",
    "PD_BRAND_NAME",
    "PD_BRAND_TAGLINE",
    "PD_PRIMARY_COLOR",
    "PD_API_KEY",
    "JWT_SECRET",
    "API_PORT",
    "PD_PORT",
    "OSINT_PORT",
    "REDIS_PORT",
}
PLACEHOLDER_VALUES = {
    "change-me",
    "change-me-strong",
    "dev-local-key",
    "sk-local-change-me",
    "pk-...",
}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {line_number} is not KEY=VALUE format")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            raise ValueError(f"line {line_number} has an empty key")
        values[key] = value
    return values


def validate_config(values: dict[str, str], production: bool = False) -> list[str]:
    issues: list[str] = []
    missing = sorted(key for key in REQUIRED_KEYS if not values.get(key, "").strip())
    issues.extend(f"missing:{key}" for key in missing)

    environment = values.get("APP_ENV", "").strip().lower()
    if environment not in {"local", "production"}:
        issues.append("APP_ENV must be local or production")
    if production:
        environment = "production"

    if not HEX_COLOR.fullmatch(values.get("PD_PRIMARY_COLOR", "").strip()):
        issues.append("PD_PRIMARY_COLOR must be a six-digit hex color")
    if not 1 <= len(values.get("PD_BRAND_NAME", "")) <= 80:
        issues.append("PD_BRAND_NAME must contain 1-80 characters")
    if not 1 <= len(values.get("PD_BRAND_TAGLINE", "")) <= 160:
        issues.append("PD_BRAND_TAGLINE must contain 1-160 characters")

    ports: dict[str, int] = {}
    for key in ("API_PORT", "PD_PORT", "OSINT_PORT", "REDIS_PORT"):
        raw_value = values.get(key, "")
        try:
            port = int(raw_value)
            if not 1 <= port <= 65535:
                raise ValueError
            ports[key] = port
        except ValueError:
            issues.append(f"{key} must be an integer between 1 and 65535")
    if "API_PORT" in ports and "PD_PORT" in ports and ports["API_PORT"] != ports["PD_PORT"]:
        issues.append("API_PORT and PD_PORT must match for the Compose API profile")

    public_url = values.get("PUBLIC_BASE_URL", "").strip()
    if environment == "production":
        if not values.get("PD_API_KEY", "").startswith("prod-"):
            issues.append("production PD_API_KEY must start with prod-")
        if len(values.get("JWT_SECRET", "")) < 32 or values.get("JWT_SECRET") in PLACEHOLDER_VALUES:
            issues.append("production JWT_SECRET must be a non-placeholder value of at least 32 characters")
        if not public_url.startswith("https://"):
            issues.append("production PUBLIC_BASE_URL must use https://")
        for key in ("PG_PASSWORD", "NEO4J_PASSWORD", "REDIS_PASSWORD", "N8N_ENCRYPTION_KEY"):
            if values.get(key) in PLACEHOLDER_VALUES:
                issues.append(f"production {key} must be replaced")

    return issues


def public_demo_issues(repo_root: Path) -> list[str]:
    forbidden = ("PD_API_KEY", "JWT_SECRET", "LITELLM_MASTER_KEY", "change-me-strong")
    issues: list[str] = []
    demo_root = repo_root / "demo"
    for required_file in ("index.html", "tester.html", "styles.css", "script.js", "demo-data.json", "README.md", ".nojekyll"):
        if not (demo_root / required_file).is_file():
            issues.append(f"public demo missing required asset:{required_file}")
    for path in demo_root.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for marker in forbidden:
            if marker in content:
                issues.append(f"public demo contains forbidden marker:{path.relative_to(repo_root)}:{marker}")
        if path.suffix == ".html" and ("127.0.0.1" in content or "localhost:" in content):
            issues.append(f"public demo contains internal endpoint reference:{path.relative_to(repo_root)}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Prospect Dominion customer deployment environment")
    parser.add_argument("--env-file", type=Path, default=Path("deploy/customer.env.example"))
    parser.add_argument("--production", action="store_true", help="apply production security requirements")
    parser.add_argument("--check-public-demo", action="store_true", help="scan public demo assets for secret markers")
    args = parser.parse_args()

    try:
        values = load_env_file(args.env_file)
        issues = validate_config(values, production=args.production)
        if args.check_public_demo:
            issues.extend(public_demo_issues(Path(__file__).resolve().parent.parent))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, indent=2))
        return 1

    payload = {
        "status": "valid" if not issues else "invalid",
        "env_file": str(args.env_file),
        "environment": values.get("APP_ENV", "").strip().lower(),
        "brand_name": values.get("PD_BRAND_NAME", ""),
        "issues": issues,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
