import base64
import hashlib
import hmac
import json

import httpx
import pytest

from app.resend import ResendSender, verify_webhook


def test_resend_sender_posts_expected_payload() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "msg-1"})

    sender = ResendSender("re_test", httpx.Client(transport=httpx.MockTransport(handler)))
    assert sender.send({"from": "Team <team@acme.test>", "to": "dana@acme.test", "subject": "Hello", "html": "<p>Hello</p>"}) == "msg-1"
    assert captured["authorization"] == "Bearer re_test"


def test_resend_webhook_signature_is_verified() -> None:
    raw = b'{"id":"evt-1"}'
    raw_key = b"a webhook signing key"
    secret = "whsec_" + base64.b64encode(raw_key).decode().rstrip("=")
    timestamp = "1700000000"
    signature = base64.b64encode(hmac.new(raw_key, b"message-1." + timestamp.encode() + b"." + raw, hashlib.sha256).digest()).decode()
    verify_webhook(raw, {"svix-id": "message-1", "svix-timestamp": timestamp, "svix-signature": f"v1,{signature}"}, secret=secret, now=1700000000)
    with pytest.raises(ValueError):
        verify_webhook(raw + b"!", {"svix-id": "message-1", "svix-timestamp": timestamp, "svix-signature": f"v1,{signature}"}, secret=secret, now=1700000000)
