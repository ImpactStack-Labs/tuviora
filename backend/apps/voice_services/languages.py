"""Supported languages for Tuviora's Voice assistant."""

LANGUAGES = {
    "1": {
        "code": "eng",
        "name": "English",
        "welcome": "Welcome to Tuviora.",
    },
    "2": {
        "code": "swa",
        "name": "Kiswahili",
        "welcome": "Karibu Tuviora.",
    },
    "3": {
        "code": "lug",
        "name": "Luganda",
        "welcome": "Tukwaniriza ku Tuviora.",
    },
}

LANGUAGE_SELECTION = (
    "Welcome to Tuviora. "
    "For English, press 1. "
    "Kwa Kiswahili, bonyeza 2. "
    "Okulonda Oluganda, nyiga 3."
)

MENU_OPTIONS = {
    "1": "event_information",
    "2": "venue_directions",
    "3": "registration_assistance",
    "0": "end_call",
}
