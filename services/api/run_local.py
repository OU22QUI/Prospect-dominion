from __future__ import annotations

import os
import sys

from app.main import resolve_runtime_port


def describe_key_state(api_key: str | None) -> str:
    if not api_key:
        return "API key is not configured"
    if len(api_key) <= 6:
        return "API key is configured and masked internally"
    prefix = api_key[:2]
    suffix = api_key[-2:]
    return f"API key configured ({prefix}...{suffix})"


if __name__ == "__main__":
    port = resolve_runtime_port()
    if not os.getenv("PD_API_KEY"):
        os.environ["PD_API_KEY"] = "dev-local-key"
    print(f"Starting Prospect Dominion API on http://127.0.0.1:{port}")
    print(describe_key_state(os.environ.get("PD_API_KEY")))
    os.environ["PD_PORT"] = str(port)

    import uvicorn

    sys.stdout.flush()
    uvicorn.run("app.main:app", host="127.0.0.1", port=port)
