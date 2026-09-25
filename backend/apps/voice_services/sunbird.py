"""Sunbird AI text-to-speech integration for Tuviora."""

import os

import requests

SUNBIRD_SPEECH_URL = (
    "https://api.sunbird.ai/tasks/audio/speech"
)

SUPPORTED_LANGUAGES = {
    "eng": "English",
    "swa": "Kiswahili",
    "lug": "Luganda",
}


class SunbirdError(Exception):
    """Raised when Sunbird speech generation fails."""


def generate_speech(text, language="eng"):
    """Generate speech and return Sunbird's response."""

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: {language}"
        )

    api_key = os.getenv("SUNBIRD_API_KEY")

    if not api_key:
        raise SunbirdError(
            "SUNBIRD_API_KEY is not configured."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    payload = {
        "text": text,
        "language": language,
        "response_mode": "url",
    }

    try:
        response = requests.post(
            SUNBIRD_SPEECH_URL,
            headers=headers,
            json=payload,
            timeout=90,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:
        raise SunbirdError(
            "Sunbird speech generation failed."
        ) from error
