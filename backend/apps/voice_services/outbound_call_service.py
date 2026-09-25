"""Outbound Africa's Talking voice call placement for Tuviora."""

import africastalking
from django.conf import settings


class VoiceCallError(Exception):
    """Raised when an outbound voice call cannot be placed."""


def place_call(phone_number):
    """Place an outbound call from Tuviora's Africa's Talking voice number."""
    username = getattr(settings, "AFRICASTALKING_USERNAME", "")
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
    voice_number = getattr(settings, "AT_VOICE_NUMBER", "")

    if not all((username, api_key, voice_number)):
        raise VoiceCallError(
            "Africa's Talking Voice is not fully configured."
        )

    try:
        africastalking.initialize(username, api_key)
        africastalking.Voice.call(voice_number, [phone_number])
    except Exception as exc:
        raise VoiceCallError("Voice call request failed.") from exc
