"""Manage private event conference sessions."""

import secrets

from django.db import transaction
from django.utils import timezone

from .conference import can_manage_conference
from .models import EventConference
from .conference_provider import send_conference_command


class ConferencePermissionError(Exception):
    """The user cannot manage this event's conference."""


class ConferenceStateError(Exception):
    """The requested conference state transition is invalid."""


@transaction.atomic
def start_conference(event, user):
    """Create or activate a conference for the event organizer."""
    if not can_manage_conference(event, user):
        raise ConferencePermissionError(
            "Only the event organizer can start a conference."
        )

    conference, created = EventConference.objects.select_for_update().get_or_create(
        event=event,
        defaults={
            "organizer": user,
            "room_name": f"tuviora_{secrets.token_hex(16)}",
        },
    )

    if conference.status == EventConference.Status.ENDED:
        raise ConferenceStateError(
            "This conference has already ended."
        )

    if conference.status == EventConference.Status.ACTIVE:
        return conference

    conference.status = EventConference.Status.ACTIVE
    conference.started_at = timezone.now()
    conference.save(update_fields=["status", "started_at"])

    return conference


@transaction.atomic
def end_conference(event, user, *, notify_provider=False):
    """End an active conference; only its organizer may do so."""
    if not can_manage_conference(event, user):
        raise ConferencePermissionError(
            "Only the event organizer can end a conference."
        )

    try:
        conference = EventConference.objects.select_for_update().get(
            event=event,
        )
    except EventConference.DoesNotExist as exc:
        raise ConferenceStateError(
            "This event does not have a conference."
        ) from exc

    if conference.status != EventConference.Status.ACTIVE:
        raise ConferenceStateError(
            "Only an active conference can be ended."
        )

    if notify_provider:
        # Disconnect callers before recording a successful end.
        send_conference_command(
            conference.room_name,
            "hup",
            participant="all",
        )

    conference.status = EventConference.Status.ENDED
    conference.ended_at = timezone.now()
    conference.save(update_fields=["status", "ended_at"])

    return conference
