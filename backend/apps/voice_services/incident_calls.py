"""Critical-incident voice call escalation, organizer/managers only."""

from datetime import timedelta

from django.utils import timezone

from apps.events.models import EventMembership, Incident
from apps.sms.models import SMSPreference

from .models import PendingVoiceCall
from .outbound_call_service import VoiceCallError, place_call

PENDING_CALL_LIFETIME = timedelta(minutes=10)


class IncidentCallStateError(Exception):
    """This incident is not eligible for a team call."""


def _build_message(incident):
    return (
        f"This is Tuviora. A critical incident has been reported "
        f"for {incident.event.name}. Category: "
        f"{incident.get_category_display()}. {incident.title}. "
        f"Please open the app for details."
    )


def call_team_for_incident(incident):
    """Call the organizer and event managers about a critical incident.

    Permission checking is the caller's responsibility (see
    IncidentCallTeamView) — by the time this runs, the requester has
    already been confirmed as the organizer or an event manager.
    """
    if incident.severity != Incident.Severity.CRITICAL:
        raise IncidentCallStateError(
            "Calls are only available for critical incidents."
        )

    recipient_ids = {incident.event.organizer_id}
    recipient_ids.update(
        EventMembership.objects.filter(
            event=incident.event,
            role=EventMembership.Role.MANAGER,
        ).values_list("user_id", flat=True)
    )

    # sms_enabled is deliberately not checked: a critical safety call
    # isn't gated by marketing SMS consent, only by having a number on file.
    phone_numbers = list(
        SMSPreference.objects.filter(user_id__in=recipient_ids)
        .exclude(phone_number="")
        .values_list("phone_number", flat=True)
    )

    message = _build_message(incident)
    dialed = 0
    failed = 0

    for phone_number in phone_numbers:
        PendingVoiceCall.objects.create(
            phone_number=phone_number,
            message=message,
            expires_at=timezone.now() + PENDING_CALL_LIFETIME,
        )
        try:
            place_call(phone_number)
            dialed += 1
        except VoiceCallError:
            failed += 1

    return {
        "dialed": dialed,
        "failed": failed,
        "skipped": len(recipient_ids) - len(phone_numbers),
    }
