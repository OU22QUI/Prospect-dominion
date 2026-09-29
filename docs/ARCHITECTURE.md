# Pilot architecture (current foundation)

```text
operator (future authenticated UI)
        |
     HTTPS domain (not configured in this repository)
        |
      Caddy  ---> FastAPI API ---> Postgres (migrations/system-of-record schema)
                         |
                         +--> Redis (rate limiting)
```

`demo` is separate: Caddy serves static files from `demo/` with sample data only. Neo4j, Qdrant, LiteLLM, Crawl4AI, Mem0, n8n, Postal, and observability overlays are not required by `pilot` and must not be described as pilot capabilities.
