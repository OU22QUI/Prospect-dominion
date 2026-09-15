from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Prospect Dominion Memory Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mem0", "status": "ready"}
