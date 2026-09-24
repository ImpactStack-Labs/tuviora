"""Africa's Talking XML responses for private event conferences."""

from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings
from django.http import HttpResponse


def conference_response(room_name, *, is_organizer=False):
    """Build XML for an already-authorized conference participant.

    Authorization must happen before this function is called.
    """
    if not room_name or not room_name.replace("_", "").isalnum():
        raise ValueError("Invalid conference room name")

    limit = settings.VOICE_CONFERENCE_MAX_PARTICIPANTS

    if not 2 <= limit <= 50:
        raise ValueError("Conference participant limit must be 2–50")

    root = Element("Response")

    conference = SubElement(
        root,
        "Conference",
        {
            "maxParticipants": str(limit),
            "record": "false",
            "beep": "onEnter",
            "muted": "false",
            "startOnEnter": (
                "true" if is_organizer else "false"
            ),
            "endOnExit": (
                "true" if is_organizer else "false"
            ),
            "flags": (
                "moderator" if is_organizer else "joinOnly"
            ),
        },
    )

    conference.text = room_name

    xml = tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )

    return HttpResponse(
        xml,
        content_type="application/xml",
    )
