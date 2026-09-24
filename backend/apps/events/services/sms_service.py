"""Reusable Africa's Talking SMS service for Tuviora."""

import logging
import re

import africastalking
from django.conf import settings

logger = logging.getLogger(__name__)

PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class SMSServiceError(Exception):
    """Raised when an SMS cannot be submitted successfully."""


def validate_phone_number(phone_number):
    """Require an international E.164-style phone number."""
    if not isinstance(phone_number, str):
        raise ValueError("Phone number must be a string.")

    phone_number = phone_number.strip()

    if not PHONE_PATTERN.fullmatch(phone_number):
        raise ValueError(
            "Enter a valid international phone number, "
            "for example +256700123456."
        )

    return phone_number


def send_sms(phone_number, message):
    """Submit an SMS and return Africa's Talking's delivery response."""
    recipient = validate_phone_number(phone_number)

    if not isinstance(message, str) or not message.strip():
        raise ValueError("SMS message cannot be empty.")

    if not getattr(settings, "SMS_ENABLED", False):
        raise SMSServiceError(
            "SMS sending is disabled."
        )

    username = getattr(settings, "AFRICASTALKING_USERNAME", "")
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
    sender_id = getattr(settings, "AFRICASTALKING_SENDER_ID", "")

    if not username or not api_key:
        raise SMSServiceError(
            "Africa's Talking SMS credentials are not configured."
        )

    try:
        africastalking.initialize(username, api_key)

        sms = africastalking.SMS

        kwargs = {
            "message": message.strip(),
            "recipients": [recipient],
        }

        if sender_id:
            kwargs["sender_id"] = sender_id

        response = sms.send(**kwargs)

        recipients = response.get("SMSMessageData", {}).get(
            "Recipients", []
        )

        if not recipients:
            raise SMSServiceError(
                "Africa's Talking returned no recipient status."
            )

        status = recipients[0].get("status", "")

        if status not in {"Success", "Sent"}:
            raise SMSServiceError(
                f"SMS was not accepted: {status or 'Unknown status'}"
            )

        return response

    except SMSServiceError:
        raise
    except Exception as exc:
        logger.exception("Africa's Talking SMS submission failed.")
        raise SMSServiceError(
            "SMS could not be submitted. Please try again later."
        ) from exc
