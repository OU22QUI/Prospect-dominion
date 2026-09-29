"""Small, explicit authentication primitives for the single-tenant pilot."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any


def hash_password(password: str, salt: str | None = None) -> str:
    if len(password) < 12:
        raise ValueError("password must be at least 12 characters")
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_value.encode(), 310_000)
    return f"pbkdf2_sha256$310000${salt_value}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds))
        return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
    except (TypeError, ValueError):
        return False


def _secret() -> bytes:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32 or secret in {"change-me", "change-me-strong"}:
        raise RuntimeError("a non-placeholder JWT_SECRET of at least 32 characters is required")
    return secret.encode()


def issue_token(*, user_id: str, tenant_id: str, expires_minutes: int = 480) -> str:
    payload = {
        "sub": user_id,
        "tenant": tenant_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)).timestamp()),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(_secret(), encoded, hashlib.sha256).digest()
    return f"pd1.{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def verify_token(token: str) -> dict[str, Any]:
    try:
        version, payload_part, signature_part = token.split(".", 2)
        if version != "pd1":
            raise ValueError
        expected = hmac.new(_secret(), payload_part.encode(), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        if not hmac.compare_digest(expected, actual):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4)))
        if int(payload["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError
        if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("tenant"), str):
            raise ValueError
        return payload
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("invalid or expired session token") from None
