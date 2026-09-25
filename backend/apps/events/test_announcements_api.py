from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Event,
    EventAnnouncement,
    EventMembership,
    EventRegistration,
)

User = get_user_model()
SEND = "apps.events.services.announcements.send_attendee_sms"
COUNTS = {"submitted": 1, "failed": 0, "skipped": 0}


def make_event(organizer, days_ahead=7, name="Demo Event"):
    return Event.objects.create(
        organizer=organizer,
        name=name,
        category=Event.Category.CONFERENCE,
        date=timezone.localdate() + timedelta(days=days_ahead),
        start_time="09:00",
        end_time="17:00",
        event_format=Event.EventFormat.PHYSICAL,
        venue="Kampala",
        status=Event.Status.PUBLISHED,
    )


class AnnouncementAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="org")
        self.manager = User.objects.create_user(username="mgr")
        self.member = User.objects.create_user(username="mem")
        self.outsider = User.objects.create_user(username="out")
        self.confirmed = User.objects.create_user(username="conf")
        self.pending = User.objects.create_user(username="pend")
        self.cancelled = User.objects.create_user(username="canc")
        self.event = make_event(self.organizer)
        EventMembership.objects.create(
            event=self.event, user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.event, user=self.member,
            role=EventMembership.Role.MEMBER,
        )
        for user, reg_status in (
            (self.confirmed, EventRegistration.Status.CONFIRMED),
            (self.pending, EventRegistration.Status.PAYMENT_PENDING),
            (self.cancelled, EventRegistration.Status.CANCELLED),
        ):
            EventRegistration.objects.create(
                event=self.event, user=user, status=reg_status,
            )
        self.url = f"/api/events/{self.event.id}/announcements/"

    def post(self, user, message="Doors open at 8am."):
        self.client.force_authenticate(user=user)
        return self.client.post(self.url, {"message": message}, format="json")

    @patch(SEND, return_value=COUNTS)
    def test_organizer_sends_to_confirmed_attendees_only(self, send):
        response = self.post(self.organizer)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send.assert_called_once_with([self.confirmed.id], "Doors open at 8am.")
        self.assertEqual(response.data["submitted"], 1)
        announcement = EventAnnouncement.objects.get()
        self.assertEqual(announcement.sent_by, self.organizer)

    @patch(SEND, return_value=COUNTS)
    def test_manager_can_send(self, send):
        self.assertEqual(self.post(self.manager).status_code, 201)

    @patch(SEND, return_value=COUNTS)
    def test_member_forbidden_and_outsider_not_found(self, send):
        self.assertEqual(self.post(self.member).status_code, 403)
        self.assertEqual(self.post(self.outsider).status_code, 404)
        send.assert_not_called()

    @patch(SEND, return_value=COUNTS)
    def test_rejects_empty_and_overlong_messages(self, send):
        self.assertEqual(self.post(self.organizer, "   ").status_code, 400)
        self.assertEqual(self.post(self.organizer, "x" * 481).status_code, 400)
        send.assert_not_called()

    def test_history_is_scoped_to_event(self):
        other = make_event(self.organizer, name="Other")
        EventAnnouncement.objects.create(event=self.event, message="mine")
        EventAnnouncement.objects.create(event=other, message="theirs")
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([a["message"] for a in response.data], ["mine"])


class ReminderCommandTests(APITestCase):
    @patch(SEND, return_value=COUNTS)
    def test_reminds_tomorrows_events_once(self, send):
        organizer = User.objects.create_user(username="org")
        attendee = User.objects.create_user(username="att")
        tomorrow = make_event(organizer, days_ahead=1, name="Tomorrow")
        make_event(organizer, days_ahead=2, name="Later")
        EventRegistration.objects.create(
            event=tomorrow, user=attendee,
            status=EventRegistration.Status.CONFIRMED,
        )

        call_command("send_event_reminders", stdout=StringIO())
        call_command("send_event_reminders", stdout=StringIO())

        send.assert_called_once()
        user_ids, message = send.call_args.args
        self.assertEqual(user_ids, [attendee.id])
        self.assertTrue(message.startswith("Reminder: Tomorrow is tomorrow"))
        reminder = EventAnnouncement.objects.get()
        self.assertIsNone(reminder.sent_by)
        self.assertEqual(reminder.event, tomorrow)
