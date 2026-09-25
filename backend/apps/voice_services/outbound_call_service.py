"""Outbound Africa's Talking voice call placement for Tuviora."""

import logging

import africastalking
from django.conf import settings

logger = logging.getLogger(__name__)


class VoiceCallError(Exception):
    """Raised when an outbound voice call cannot be placed."""


def place_call(phone_number):
    """Place an outbound call from Tuviora's Africa's Talking voice number.

    Returns Africa's Talking's raw response dict on success. Raises
    VoiceCallError if the request fails or the provider does not report
    the call as queued.
    """
    username = getattr(settings, "AFRICASTALKING_USERNAME", "")
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
    voice_number = getattr(settings, "AT_VOICE_NUMBER", "")

    if not all((username, api_key, voice_number)):
        raise VoiceCallError(
            "Africa's Talking Voice is not fully configured."
        )

    try:
        africastalking.initialize(username, api_key)
        response = africastalking.Voice.call(voice_number, [phone_number])

        entries = response.get("entries", [])

        if not entries:
            raise VoiceCallError(
                "Africa's Talking returned no call entries."
            )

        status = entries[0].get("status", "")

        if status != "Queued":
            raise VoiceCallError(
                f"Call was not queued: {status or 'Unknown status'}"
            )

        return response

    except VoiceCallError:
        raise
    except Exception as exc:
        logger.exception("Africa's Talking voice call request failed.")
        raise VoiceCallError("Voice call request failed.") from exc
