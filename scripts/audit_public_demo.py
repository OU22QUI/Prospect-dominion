from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_ROOT = REPO_ROOT / "demo"
REQUIRED_FILES = ("index.html", "tester.html", "styles.css", "config.js", "script.js", "demo-data.json", "favicon.svg", "og-preview.svg", "README.md", ".nojekyll")
FORBIDDEN_MARKERS = ("PD_API_KEY", "JWT_SECRET", "LITELLM_MASTER_KEY", "change-me-strong", "localhost:", "127.0.0.1")
REQUIRED_IDS = ("accountList", "detailCompany", "runAction", "walkthroughForm", "formStatus", "guideStrip", "resetDemo", "accountSearch", "stageFilter", "intentFilter")


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        for key in ("href", "src"):
            value = attributes.get(key)
            if value:
                self.references.append(value)
        element_id = attributes.get("id")
        if element_id:
            self.ids.add(element_id)


def main() -> int:
    issues: list[str] = []

    for filename in REQUIRED_FILES:
        if not (DEMO_ROOT / filename).is_file():
            issues.append(f"missing required asset: {filename}")

    index_path = DEMO_ROOT / "index.html"
    index = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    parser = AssetParser()
    parser.feed(index)

    for reference in parser.references:
        if reference.startswith(("#", "http://", "https://", "mailto:")):
            continue
        if not (DEMO_ROOT / reference).is_file():
            issues.append(f"broken local asset reference: {reference}")

    for required_id in REQUIRED_IDS:
        if required_id not in parser.ids:
            issues.append(f"missing interaction hook: {required_id}")

    try:
        payload = json.loads((DEMO_ROOT / "demo-data.json").read_text(encoding="utf-8"))
        accounts = payload.get("accounts")
        if not isinstance(accounts, list) or not accounts:
            issues.append("demo-data.json must contain a non-empty accounts list")
        for index, account in enumerate(accounts or []):
            for field in ("company", "intent", "stage", "score", "signal", "path"):
                if not account.get(field):
                    issues.append(f"account {index} missing field: {field}")
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        issues.append(f"invalid demo-data.json: {exc}")

    for path in DEMO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for marker in FORBIDDEN_MARKERS:
            if marker in content:
                issues.append(f"forbidden marker {marker!r} in {path.relative_to(REPO_ROOT)}")

    styles = (DEMO_ROOT / "styles.css").read_text(encoding="utf-8")
    if "@media (max-width: 900px)" not in styles or "@media (max-width: 560px)" not in styles:
        issues.append("responsive breakpoints are incomplete")
    if "prefers-reduced-motion" not in styles:
        issues.append("missing prefers-reduced-motion support")

    payload = {"status": "valid" if not issues else "invalid", "issues": issues}
    print(json.dumps(payload, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())