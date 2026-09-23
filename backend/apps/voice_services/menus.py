"""Language-specific menus for Tuviora's Voice assistant."""

MESSAGES = {
    "eng": {
        "main": (
            "Welcome to Tuviora. "
            "For event information, press 1. "
            "For venue and directions, press 2. "
            "For registration assistance, press 3. "
            "To change your language, press 9. "
            "To end the call, press 0."
        ),
        "event_information": (
            "Event information will be available shortly. "
            "Press 9 to return to the main menu."
        ),
        "venue_directions": (
            "Venue and directions assistance will be available shortly. "
            "Press 9 to return to the main menu."
        ),
        "registration_assistance": (
            "Registration assistance will be available shortly. "
            "Press 9 to return to the main menu."
        ),
        "invalid": "Invalid selection. Please try again.",
        "goodbye": "Thank you for calling Tuviora. Goodbye.",
    },
    "swa": {
        "main": (
            "Karibu Tuviora. "
            "Kwa taarifa za tukio, bonyeza 1. "
            "Kwa maelekezo ya kufika kwenye eneo la tukio, bonyeza 2. "
            "Kwa msaada wa usajili, bonyeza 3. "
            "Kubadilisha lugha, bonyeza 9. "
            "Kumaliza simu, bonyeza 0."
        ),
        "event_information": (
            "Taarifa za tukio zitapatikana hivi karibuni. "
            "Bonyeza 9 kurudi kwenye menyu kuu."
        ),
        "venue_directions": (
            "Maelekezo ya kufika kwenye eneo la tukio "
            "yatapatikana hivi karibuni. "
            "Bonyeza 9 kurudi kwenye menyu kuu."
        ),
        "registration_assistance": (
            "Msaada wa usajili utapatikana hivi karibuni. "
            "Bonyeza 9 kurudi kwenye menyu kuu."
        ),
        "invalid": "Chaguo si sahihi. Tafadhali jaribu tena.",
        "goodbye": "Asante kwa kupiga simu Tuviora. Kwaheri.",
    },
    "lug": {
        "main": (
            "Tukwaniriza ku Tuviora. "
            "Okufuna amawulire agakwata ku mukolo, nyiga 1. "
            "Okufuna endagiriro y'ekifo ky'omukolo, nyiga 2. "
            "Okufuna obuyambi mu kwewandiisa, nyiga 3. "
            "Okukyusa olulimi, nyiga 9. "
            "Okumaliriza essimu, nyiga 0."
        ),
        "event_information": (
            "Amawulire agakwata ku mukolo gajja kubaawo mu bbanga ttono. "
            "Nyiga 9 okuddayo ku menu enkulu."
        ),
        "venue_directions": (
            "Endagiriro y'ekifo ky'omukolo ejja kubaawo mu bbanga ttono. "
            "Nyiga 9 okuddayo ku menu enkulu."
        ),
        "registration_assistance": (
            "Obuyambi mu kwewandiisa bujja kubaawo mu bbanga ttono. "
            "Nyiga 9 okuddayo ku menu enkulu."
        ),
        "invalid": "Ky'olonze si kituufu. Gezaako nate.",
        "goodbye": "Webale okukubira Tuviora. Weraba.",
    },
}


def get_message(language, message_key):
    """Return a voice message in the selected language."""
    messages = MESSAGES.get(language, MESSAGES["eng"])
    return messages.get(message_key, messages["invalid"])
