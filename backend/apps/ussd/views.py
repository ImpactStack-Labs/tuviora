"""Africa's Talking USSD callback for Tuviora."""

import re

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.voice_services.events import get_public_event, get_registration


MAIN_MENU = (
    "CON Welcome to Tuviora\n"
    "1. Event information\n"
    "2. Check registration\n"
    "3. Staff incident report\n"
    "0. Exit"
)


def reply(prefix, message):
    return HttpResponse(f"{prefix} {message}", content_type="text/plain")


@csrf_exempt
@require_POST
def ussd_callback(request):
    """Respond to Africa's Talking's cumulative, star-separated input."""
    session_id = request.POST.get("sessionId", "")
    phone = request.POST.get("phoneNumber", "")
    text = request.POST.get("text", "")

    if (
        not session_id
        or len(session_id) > 128
        or not re.fullmatch(r"\+[1-9]\d{7,14}", phone)
        or len(text) > 160
    ):
        return reply("END", "Unable to process this session. Please try again.")

    if text == "":
        return HttpResponse(MAIN_MENU, content_type="text/plain")

    parts = text.split("*")

    if parts[-1] == "0":
        return reply("END", "Thank you for using Tuviora.")

    if parts[0] == "1":
        if len(parts) == 1:
            return reply("CON", "Enter the published event ID:")
        if len(parts) != 2 or not parts[1].isdigit():
            return reply("END", "Invalid event ID. Please dial again.")

        try:
            event = get_public_event(parts[1])
        except Exception:
            return reply("END", "Event information is unavailable. Please try later.")

        if event is None:
            return reply("END", "Published event not found.")

        return reply(
            "END",
            f"{event.name}: {event.date:%d %b %Y}, "
            f"{event.start_time:%H:%M} at {event.venue or 'online'}.",
        )

    if parts[0] == "2":
        if len(parts) == 1:
            return reply("CON", "Enter the event ID:")
        if len(parts) != 2 or not parts[1].isdigit():
            return reply("END", "Invalid event ID. Please dial again.")

        try:
            registration = get_registration(parts[1], phone)
        except Exception:
            return reply(
                "END", "Registration information is unavailable. Please try later."
            )

        if registration is None:
            return reply("END", "No registration found for this event.")

        message = (
            f"{registration.event.name}: {registration.get_status_display()}"
        )
        if registration.ticket_type is not None:
            message += f", {registration.ticket_type.name} ticket"
        if registration.amount_due is not None:
            message += f", {registration.amount_due} {registration.currency} due"

        return reply("END", message + ".")

    if parts[0] == "3":
        return reply(
            "END",
            "Staff reporting is being connected. Contact the organizer directly.",
        )

    return reply("CON", "Invalid choice.\n" + MAIN_MENU.removeprefix("CON "))
