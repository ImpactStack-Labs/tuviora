"""Africa's Talking conference management API client."""

import requests

from django.conf import settings


CONFERENCE_API_URL = (
    "https://voice.africastalking.com/conference"
)


class ConferenceProviderError(Exception):
    """Africa's Talking could not complete a conference command."""


def send_conference_command(
    room_name,
    command,
    *,
    participant=None,
):
    """Send a conference management command to Africa's Talking.

    This function must only be called by trusted server-side code.
    """
    allowed_commands = {
        "hup",
        "kick",
        "lock",
        "unlock",
        "mute",
        "unmute",
    }

    if command not in allowed_commands:
        raise ConferenceProviderError(
            "Unsupported conference command."
        )

    username = getattr(
        settings,
        "AT_VOICE_USERNAME",
        "",
    )
    api_key = getattr(
        settings,
        "AT_VOICE_API_KEY",
        "",
    )
    phone_number = getattr(
        settings,
        "AT_VOICE_NUMBER",
        "",
    )

    if not all((username, api_key, phone_number)):
        raise ConferenceProviderError(
            "Africa's Talking Voice is not fully configured."
        )

    payload = {
        "username": username,
        "phoneNumber": phone_number,
        "command": command,
        "roomName": room_name,
    }

    if participant is not None:
        payload["participant"] = participant

    try:
        response = requests.post(
            CONFERENCE_API_URL,
            json=payload,
            headers={
                "apiKey": api_key,
                "Accept": "application/json",
            },
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        raise ConferenceProviderError(
            "Conference provider request failed."
        ) from exc

    if not isinstance(result, dict) or result.get("status") is not True:
        raise ConferenceProviderError(
            "Conference provider rejected the command."
        )

    return result
