"""Attendee feedback shared by the web API and USSD."""

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

    # ponytail: no DB unique constraint; two simultaneous first submissions
    # could duplicate. Add UniqueConstraint(event, attendee) if that shows up.
    return Feedback.objects.update_or_create(
        event=event,
        attendee=user,
        defaults={"rating": rating, "comment": comment},
    )
