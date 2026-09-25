"""Africa's Talking USSD callback for Tuviora."""

import re

from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.events.models import EventRegistration, TicketType
from apps.events.services.feedback import submit_feedback
from apps.events.services.registration import RegistrationError, register_for_event
from apps.sms.models import SMSPreference
from apps.sms.services.sms_service import SMSServiceError, send_sms
from apps.voice_services.events import get_public_event, get_registration


MAIN_MENU = (
    "CON Welcome to Tuviora\n"
    "1. Event information\n"
    "2. Check registration\n"
    "3. Staff incident report\n"
    "4. Register for an event\n"
    "5. Rate an event\n"
    "0. Exit"
)


def reply(prefix, message):
    return HttpResponse(f"{prefix} {message}", content_type="text/plain")


def rate_event(parts, phone):
    """Option 5: rate a confirmed registration, then optionally comment."""
    if len(parts) == 1:
        return reply("CON", "Enter the event ID:")
    if not parts[1].isdigit():
        return reply("END", "Invalid event ID. Please dial again.")

    try:
        registration = get_registration(parts[1], phone)
    except Exception:
        return reply("END", "Feedback is unavailable. Please try later.")

    if (
        registration is None
        or registration.status != EventRegistration.Status.CONFIRMED
    ):
        return reply("END", "No registration found for this event.")

    if len(parts) == 2:
        return reply(
            "CON",
            f"Rate {registration.event.name} from 1 (poor) to 5 (excellent):",
        )
    if parts[2] not in {"1", "2", "3", "4", "5"}:
        return reply("END", "Invalid rating. Please dial again.")
    if len(parts) == 3:
        return reply("CON", "Add a comment, or enter 9 to skip:")

    # Africa's Talking joins inputs with "*", so rejoin a comment containing it.
    comment = "*".join(parts[3:]).strip()
    try:
        submit_feedback(
            registration.event,
            registration.user,
            rating=int(parts[2]),
            comment="" if comment == "9" else comment,
        )
    except Exception:
        return reply("END", "Feedback is unavailable. Please try later.")
    return reply("END", "Thank you for your feedback.")


def register_event(parts, phone):
    """Option 4: register an existing account for a free event."""
    if len(parts) == 1:
        return reply("CON", "Enter the event ID:")
    if not parts[1].isdigit():
        return reply("END", "Invalid event ID. Please dial again.")

    site = settings.FRONTEND_BASE_URL
    preference = (
        SMSPreference.objects.select_related("user")
        .filter(phone_number=phone)
        .first()
    )
    if preference is None:
        return reply(
            "END",
            "No Tuviora account uses this phone. "
            f"Sign up at {site}/signup and add this number.",
        )

    event = get_public_event(parts[1])
    if event is None:
        return reply("END", "Published event not found.")

    ticket_types = TicketType.objects.filter(event=event, is_active=True)
    ticket_type = None
    if ticket_types.exists():
        ticket_type = ticket_types.filter(price=0).order_by("price", "pk").first()
        if ticket_type is None:
            return reply(
                "END",
                f"This event requires payment. Register at {site}/events/{event.pk}.",
            )

    if len(parts) == 2:
        return reply(
            "CON",
            f"Register for {event.name}, {event.date:%d %b} "
            f"{event.start_time:%H:%M}?\n1. Yes\n2. No",
        )
    if parts[2] != "1":
        return reply("END", "Registration cancelled.")

    try:
        register_for_event(
            event.pk,
            preference.user,
            ticket_type_id=ticket_type.pk if ticket_type else None,
        )
    except Http404:
        return reply("END", "Published event not found.")
    except RegistrationError as exc:
        return reply("END", exc.detail)

    if preference.sms_enabled:
        message = (
            f"You're registered for {event.name} on {event.date:%d %b %Y} "
            f"at {event.start_time:%H:%M}, {event.venue or 'online'}."
        )

        def confirm():
            try:
                send_sms(phone, message)
            except (SMSServiceError, ValueError):
                pass  # SMS failure never undoes the registration.

        transaction.on_commit(confirm)

    return reply("END", f"You're registered for {event.name}.")


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

    if parts[0] == "4":
        return register_event(parts, phone)

    if parts[0] == "5":
        return rate_event(parts, phone)

    return reply("CON", "Invalid choice.\n" + MAIN_MENU.removeprefix("CON "))
