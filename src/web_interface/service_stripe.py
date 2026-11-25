"""
Stripe payments of the cloud service (Stripe Checkout and refunds through the REST API).

The Web Interface never sees card data: the user pays on the Stripe Checkout page and Stripe tells the server the
result through a signed webhook (checked here with the webhook signing secret).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

import requests

API_BASE = "https://api.stripe.com/v1"
WEBHOOK_TOLERANCE_SECONDS = 300
TIMEOUT_SECONDS = 30


class StripeError(RuntimeError):
    """A Stripe call failed. The message is safe to show to an administrator (it never contains the key)."""


def _flatten(data: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
    """Stripe form encoding: {"a": {"b": 1}, "c": [{"d": 2}]} -> {"a[b]": "1", "c[0][d]": "2"}."""
    out: Dict[str, str] = {}
    for key, value in data.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if value is None:
            continue
        if isinstance(value, dict):
            out.update(_flatten(value, name))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                item_name = f"{name}[{index}]"
                if isinstance(item, dict):
                    out.update(_flatten(item, item_name))
                else:
                    out[item_name] = str(item)
        elif isinstance(value, bool):
            out[name] = "true" if value else "false"
        else:
            out[name] = str(value)
    return out


def _request(secret_key: str, method: str, path: str, data: Optional[Dict[str, Any]] = None,
             idempotency_key: str = "") -> Dict[str, Any]:
    if not str(secret_key or "").strip():
        raise StripeError("Stripe is not configured: add the secret key in the Administration Panel.")
    headers = {"Authorization": f"Bearer {secret_key.strip()}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    try:
        response = requests.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            data=_flatten(data or {}) if method.upper() != "GET" else None,
            params=_flatten(data or {}) if method.upper() == "GET" else None,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise StripeError(f"Could not reach Stripe ({type(exc).__name__}).") from exc
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 400:
        message = str(((body or {}).get("error") or {}).get("message") or f"HTTP {response.status_code}")
        raise StripeError(f"Stripe refused the request: {message}")
    return body


def key_mode(secret_key: str) -> str:
    """'test' or 'live' from the key prefix (sk_test_, rk_test_, sk_live_, rk_live_)."""
    return "live" if "_live_" in str(secret_key or "") else "test"


def check_connection(secret_key: str) -> Dict[str, Any]:
    """Cheapest call the restricted key can make (Checkout Sessions read)."""
    _request(secret_key, "GET", "/checkout/sessions", {"limit": 1})
    return {"ok": True, "mode": key_mode(secret_key)}


def create_checkout_session(secret_key: str, *, task_id: str, purpose: str, amount_cents: int, currency: str,
                            description: str, customer_email: str, success_url: str, cancel_url: str,
                            automatic_tax: bool = False, locale: str = "auto") -> Dict[str, Any]:
    price_data: Dict[str, Any] = {
        "currency": currency,
        "unit_amount": int(amount_cents),
        "product_data": {"name": description},
    }
    if automatic_tax:
        price_data["tax_behavior"] = "inclusive"
    data: Dict[str, Any] = {
        "mode": "payment",
        "line_items": [{"price_data": price_data, "quantity": 1}],
        "client_reference_id": task_id,
        "metadata": {"task_id": task_id, "purpose": purpose},
        "payment_intent_data": {"metadata": {"task_id": task_id, "purpose": purpose}},
        "success_url": success_url,
        "cancel_url": cancel_url,
        "locale": locale or "auto",
    }
    if customer_email:
        data["customer_email"] = customer_email
    if automatic_tax:
        data["automatic_tax"] = {"enabled": True}
    return _request(secret_key, "POST", "/checkout/sessions", data, idempotency_key=f"checkout-{task_id}-{purpose}-{int(time.time() // 600)}")


def get_checkout_session(secret_key: str, session_id: str) -> Dict[str, Any]:
    return _request(secret_key, "GET", f"/checkout/sessions/{session_id}")


def refund_payment(secret_key: str, payment_intent_id: str, task_id: str, reason: str = "requested_by_customer") -> Dict[str, Any]:
    return _request(
        secret_key,
        "POST",
        "/refunds",
        {"payment_intent": payment_intent_id, "reason": reason, "metadata": {"task_id": task_id}},
        idempotency_key=f"refund-{task_id}-{payment_intent_id}",
    )


def verify_webhook(payload: bytes, signature_header: str, webhook_secret: str, now: Optional[float] = None) -> Dict[str, Any]:
    """Check the Stripe-Signature header and return the event. Raises ValueError when the signature is not valid."""
    if not str(webhook_secret or "").strip():
        raise ValueError("The webhook signing secret is not configured.")
    timestamp = ""
    signatures = []
    for part in str(signature_header or "").split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if not timestamp or not signatures:
        raise ValueError("Missing Stripe signature.")
    try:
        signed_at = int(timestamp)
    except ValueError as exc:
        raise ValueError("Invalid Stripe signature timestamp.") from exc
    current = time.time() if now is None else now
    if abs(current - signed_at) > WEBHOOK_TOLERANCE_SECONDS:
        raise ValueError("The Stripe signature is too old.")
    expected = hmac.new(webhook_secret.strip().encode("utf-8"), f"{timestamp}.".encode("utf-8") + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise ValueError("The Stripe signature does not match.")
    return json.loads(payload.decode("utf-8"))
