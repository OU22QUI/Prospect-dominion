import base64

from scripts.validate_customer_config import validate_config


def test_production_config_requires_postgres_ingress_and_resend() -> None:
    values = {
        "APP_ENV": "production",
        "PUBLIC_BASE_URL": "https://pilot.example.com",
        "PD_BRAND_NAME": "Prospect Dominion",
        "PD_BRAND_TAGLINE": "Governed revenue operations",
        "PD_PRIMARY_COLOR": "#4f8ef7",
        "PD_API_KEY": "prod-" + "a" * 32,
        "JWT_SECRET": "j" * 48,
        "API_PORT": "8010",
        "PD_PORT": "8010",
        "OSINT_PORT": "8081",
        "REDIS_PORT": "6380",
        "PG_USER": "pilot",
        "PG_DB": "prospect_dominion",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "n" * 32,
        "REDIS_PASSWORD": "r" * 32,
        "N8N_ENCRYPTION_KEY": "w" * 32,
        "LITELLM_MASTER_KEY": "sk-" + "l" * 32,
    }

    issues = validate_config(values, production=True)

    assert "missing:PD_PUBLIC_HOST" in issues
    assert "missing:PD_CADDYFILE" in issues
    assert "missing:PD_DEFAULT_ROLE" in issues
    assert "missing:PG_PASSWORD" in issues
    assert "missing:RESEND_API_KEY" in issues
    assert "missing:RESEND_WEBHOOK_SECRET" in issues


def test_complete_production_config_passes_validation() -> None:
    values = {
        "APP_ENV": "production",
        "PUBLIC_BASE_URL": "https://pilot.example.com",
        "PD_BRAND_NAME": "Prospect Dominion",
        "PD_BRAND_TAGLINE": "Governed revenue operations",
        "PD_PRIMARY_COLOR": "#4f8ef7",
        "PD_API_KEY": "prod-" + "a" * 32,
        "PD_DEFAULT_ROLE": "viewer",
        "JWT_SECRET": "j" * 48,
        "API_PORT": "8010",
        "PD_PORT": "8010",
        "OSINT_PORT": "8081",
        "REDIS_PORT": "6380",
        "PG_USER": "pilot",
        "PG_PASSWORD": "p" * 32,
        "PG_DB": "prospect_dominion",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "n" * 32,
        "REDIS_PASSWORD": "r" * 32,
        "N8N_ENCRYPTION_KEY": "w" * 32,
        "LITELLM_MASTER_KEY": "sk-" + "l" * 32,
        "PD_PUBLIC_HOST": "pilot.example.com",
        "PD_CADDYFILE": "./infra/caddy/Caddyfile.production",
        "RESEND_API_KEY": "re_" + "r" * 32,
        "RESEND_WEBHOOK_SECRET": "whsec_" + base64.b64encode(b"s" * 32).decode().rstrip("="),
    }

    assert validate_config(values, production=True) == []
    local_environment = {**values, "APP_ENV": "local"}
    assert "production validation requires APP_ENV=production" in validate_config(local_environment, production=True)

    invalid_provider_config = {
        **values,
        "PD_DEFAULT_ROLE": "admin",
        "RESEND_API_KEY": "re_example-placeholder",
        "RESEND_WEBHOOK_SECRET": "whsec_not-base64",
    }
    issues = validate_config(invalid_provider_config, production=True)
    assert "production PD_DEFAULT_ROLE must be viewer; use /v1 server-issued RBAC for writes" in issues
    assert "production RESEND_API_KEY must be a configured Resend key" in issues
    assert "production RESEND_WEBHOOK_SECRET must encode a 32-byte signing key" in issues