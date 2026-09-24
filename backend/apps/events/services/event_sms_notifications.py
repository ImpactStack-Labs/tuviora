"""Consent-aware SMS notifications for Tuviora events."""

import logging

from apps.accounts.models import SMSPreference

from .sms_service import SMSServiceError, send_sms

logger = logging.getLogger(__name__)


def send_event_sms(user_ids, message):
    """
    Send an SMS to explicitly selected, opted-in users.

    The caller must verify event membership or attendee registration
    and obtain organizer approval before invoking this service.
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
