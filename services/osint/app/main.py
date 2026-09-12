from fastapi import FastAPI

app = FastAPI(title="Prospect Dominion OSINT Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, dict[str, str]]:
    return {"service": {"name": "osint", "status": "running"}}
