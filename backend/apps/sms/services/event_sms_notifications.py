"""Consent-aware SMS notifications for Tuviora."""

import logging

from apps.events.models import EventMembership
from apps.sms.models import SMSPreference

from .sms_service import SMSServiceError, send_sms

logger = logging.getLogger(__name__)


def _send_sms_to_users(user_ids, message):
    """
    Send an SMS to explicitly selected, opted-in users.

    Callers must verify event membership or attendee registration
    and obtain organizer approval before invoking this function.
    """
    if not isinstance(message, str) or not message.strip():
        raise ValueError("A non-empty SMS message is required.")

    if not user_ids:
        return {
            "submitted": 0,
            "failed": 0,
            "skipped": 0,
        }

    selected_ids = set(user_ids)

    preferences = SMSPreference.objects.filter(
        user_id__in=selected_ids,
        sms_enabled=True,
    ).exclude(
        phone_number="",
    )

    submitted = 0
    failed = 0

    for preference in preferences:
        try:
            send_sms(
                preference.phone_number,
                message.strip(),
            )
            submitted += 1
        except (SMSServiceError, ValueError):
            failed += 1
            logger.warning(
                "Event SMS submission failed for user ID %s.",
                preference.user_id,
            )

    return {
        "submitted": submitted,
        "failed": failed,
        "skipped": len(selected_ids) - submitted - failed,
    }


def send_attendee_sms(user_ids, message):
    """Send an SMS to explicitly selected, opted-in attendees."""
    return _send_sms_to_users(user_ids, message)


def send_team_sms(event, message):
    """Send an SMS to the event organizer and every accepted team member."""
    user_ids = {event.organizer_id}
    user_ids.update(
        EventMembership.objects.filter(event=event)
        .values_list("user_id", flat=True)
    )
    return _send_sms_to_users(user_ids, message)
