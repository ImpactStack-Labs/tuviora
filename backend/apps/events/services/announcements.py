"""Organizer announcements and reminders to confirmed attendees."""

from apps.sms.services.event_sms_notifications import send_attendee_sms

from ..models import EventAnnouncement, EventRegistration


def reminder_message(event):
    return (
        f"Reminder: {event.name} is tomorrow, {event.date:%d %b} "
        f"at {event.start_time:%H:%M}, {event.venue or 'online'}."
    )


def announce_to_attendees(event, message, sent_by=None):
    """SMS every confirmed attendee (consent is enforced downstream)."""
    user_ids = list(
        EventRegistration.objects.filter(
            event=event,
            status=EventRegistration.Status.CONFIRMED,
        ).values_list("user_id", flat=True)
    )
    counts = send_attendee_sms(user_ids, message)
    return EventAnnouncement.objects.create(
        event=event,
        sent_by=sent_by,
        message=message,
        **counts,
    )
