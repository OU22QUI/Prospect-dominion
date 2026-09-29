"""Minimal Resend adapter with explicit request and webhook verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Any

import httpx


class ResendSender:
    provider = "resend"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None) -> None:
        self.api_key = api_key or os.getenv("RESEND_API_KEY", "")
        self.client = client or httpx.Client(timeout=10)

    def send(self, payload: dict[str, Any]) -> str:
        if not self.api_key or self.api_key.startswith("re_example"):
            raise ValueError("RESEND_API_KEY is not configured")
        required = ("from", "to", "subject", "html")
        if not all(isinstance(payload.get(key), str) and payload[key].strip() for key in required):
            raise ValueError("send payload requires from, to, subject, and html")
        response = self.client.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {self.api_key}"}, json={key: payload[key] for key in required})
        response.raise_for_status()
        message_id = response.json().get("id")
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("Resend response did not contain an email id")
        return message_id


def verify_webhook(raw_body: bytes, headers: dict[str, str], secret: str | None = None, now: int | None = None) -> None:
    webhook_secret = secret or os.getenv("RESEND_WEBHOOK_SECRET", "")
    if not webhook_secret.startswith("whsec_"):
        raise ValueError("RESEND_WEBHOOK_SECRET is not configured")
    message_id = headers.get("svix-id", "")
    timestamp = headers.get("svix-timestamp", "")
    signature_header = headers.get("svix-signature", "")
    if not message_id or not timestamp or not signature_header:
        raise ValueError("missing Resend webhook signature headers")
    try:
        timestamp_value = int(timestamp)
    except ValueError:
        raise ValueError("invalid webhook timestamp") from None
    if abs((now or int(time.time())) - timestamp_value) > 300:
        raise ValueError("expired webhook timestamp")
    try:
        encoded_key = webhook_secret.removeprefix("whsec_")
        key = base64.b64decode(encoded_key + "=" * (-len(encoded_key) % 4))
    except ValueError:
        raise ValueError("invalid webhook secret") from None
    signed_content = f"{message_id}.{timestamp}.".encode() + raw_body
    expected = base64.b64encode(hmac.new(key, signed_content, hashlib.sha256).digest()).decode()
    signatures = [part.removeprefix("v1,") for part in signature_header.split(" ") if part.startswith("v1,")]
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise ValueError("invalid webhook signature")
