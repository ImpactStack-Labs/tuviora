from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event
from apps.events.services.announcements import (
    announce_to_attendees,
    reminder_message,
)


class Command(BaseCommand):
    help = "SMS confirmed attendees of events happening tomorrow. Run daily."

    def handle(self, *args, **options):
        today = timezone.localdate()
        events = Event.objects.filter(
            status=Event.Status.PUBLISHED,
            date=today + timedelta(days=1),
        )

        for event in events:
            already_sent = event.announcements.filter(
                sent_by__isnull=True,
                created_at__date=today,
            ).exists()

            if already_sent:
                self.stdout.write(f"{event.name}: reminder already sent today")
                continue

            result = announce_to_attendees(event, reminder_message(event))
            self.stdout.write(
                f"{event.name}: {result.submitted} sent, "
                f"{result.failed} failed, {result.skipped} skipped"
            )
