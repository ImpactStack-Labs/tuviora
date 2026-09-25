"""MarzPay collections integration (https://wallet.wearemarz.com)."""

import base64
import hashlib
import hmac
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MarzPayError(Exception):
    """Raised when a MarzPay API call cannot be completed."""


def _base_url():
    return getattr(
        settings,
        "MARZPAY_BASE_URL",
        "https://wallet.wearemarz.com/api/v1",
    )


def _auth_header():
    api_key = getattr(settings, "MARZPAY_API_KEY", "")
    api_secret = getattr(settings, "MARZPAY_API_SECRET", "")

    if not api_key or not api_secret:
        raise MarzPayError(
            "MarzPay API credentials are not configured."
        )

    credentials = base64.b64encode(
        f"{api_key}:{api_secret}".encode()
    ).decode()

    return {"Authorization": f"Basic {credentials}"}


def initiate_collection(
    *,
    amount,
    currency,
    reference,
    method="mobile_money",
    phone_number=None,
    description="",
    callback_url=None,
    country=None,
):
    """Start a MarzPay collection. Returns the provider's `data` object."""
    if method == "mobile_money" and not phone_number:
        raise MarzPayError(
            "A phone number is required for mobile money collections."
        )

    # ponytail: single-market MVP — country is a fixed setting, not
    # inferred per attendee. Add phone-prefix or explicit-country
    # resolution when Tuviora expands past Uganda.
    resolved_country = country or getattr(
        settings, "MARZPAY_DEFAULT_COUNTRY", "UG"
    )

    fields = {
        "amount": str(amount),
        "currency": currency,
        "country": resolved_country,
        "reference": reference,
        "method": method,
    }

    if phone_number:
        fields["phone_number"] = phone_number

    if description:
        fields["description"] = description[:255]

    if callback_url:
        fields["callback_url"] = callback_url

    files = {key: (None, str(value)) for key, value in fields.items()}

    try:
        response = requests.post(
            f"{_base_url()}/collect-money",
            files=files,
            headers=_auth_header(),
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.exception("MarzPay collection request failed.")
        raise MarzPayError(
            "Could not reach the payment provider. Please try again."
        ) from exc

    body = response.json() if response.content else {}

    if response.status_code >= 400 or body.get("status") != "success":
        raise MarzPayError(
            body.get("message") or "Payment could not be started."
        )

    return body["data"]


def get_transaction(transaction_id):
    try:
        response = requests.get(
            f"{_base_url()}/transactions/{transaction_id}",
            headers=_auth_header(),
            timeout=15,
        )
    except requests.RequestException as exc:
        raise MarzPayError(
            "Could not reach the payment provider."
        ) from exc

    if response.status_code >= 400:
        raise MarzPayError("Transaction could not be retrieved.")

    return response.json()


def verify_webhook_signature(raw_body, timestamp, signature_header, secret):
    """Verify a MarzPay webhook's `t={ts},v1={hex}` signature header."""
    if not timestamp or not signature_header or not secret:
        return False

    parts = dict(
        part.split("=", 1)
        for part in signature_header.split(",")
        if "=" in part
    )
    provided = parts.get("v1", "")

    if not provided:
        return False

    # Validate that provided is a well-formed hex string to prevent
    # TypeError when comparing with non-ASCII characters
    if not re.fullmatch(r"[0-9a-f]+", provided):
        return False

    if isinstance(raw_body, str):
        raw_body = raw_body.encode()

    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, provided)
