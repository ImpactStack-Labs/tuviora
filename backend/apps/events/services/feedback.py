"""Attendee feedback shared by the web API and USSD."""

from django.db import IntegrityError, transaction

from ..models import EventRegistration, Feedback


class FeedbackNotAllowed(Exception):
    """The user has no confirmed registration for the event."""


def submit_feedback(event, user, rating=None, comment=""):
    """Create or update the user's single feedback for this event."""
    is_confirmed = EventRegistration.objects.filter(
        event=event,
        user=user,
        status=EventRegistration.Status.CONFIRMED,
    ).exists()

    if not is_confirmed:
        raise FeedbackNotAllowed(
            "Only confirmed attendees can give feedback."
        )

    defaults = {"rating": rating, "comment": comment}
    try:
        with transaction.atomic():
            return Feedback.objects.update_or_create(
                event=event, attendee=user, defaults=defaults,
            )
    except IntegrityError:
        # Another simultaneous first submission won the race and created
        # the row first; the unique constraint rejected ours, so retry as
        # an update now that the row exists.
        return Feedback.objects.update_or_create(
            event=event, attendee=user, defaults=defaults,
        )
