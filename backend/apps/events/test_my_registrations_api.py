from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Event, EventRegistration


class MyRegistrationsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()

        self.organizer = user_model.objects.create_user(
            username="my_regs_organizer",
            password="test-password",
        )
        self.attendee = user_model.objects.create_user(
            username="my_regs_attendee",
            password="test-password",
        )
        self.other_attendee = user_model.objects.create_user(
            username="my_regs_other",
            password="test-password",
        )

        self.url = reverse("my-registrations-list")

    def make_event(self, name, *, days_from_today=2):
        return Event.objects.create(
            organizer=self.organizer,
            name=name,
            category=Event.Category.HACKATHON,
            description="A public event description.",
            date=timezone.localdate() + timedelta(days=days_from_today),
            start_time="09:00",
            end_time="17:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
            capacity=100,
            status=Event.Status.PUBLISHED,
            online_url="https://example.com/private-meeting",
            joining_instructions="Private joining instructions",
        )

    def test_authentication_is_required(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, (401, 403))

    def test_attendee_sees_only_their_own_registrations(self):
        my_event = self.make_event("My event")
        other_event = self.make_event("Someone else's event")

        mine = EventRegistration.objects.create(
            event=my_event,
            user=self.attendee,
        )
        EventRegistration.objects.create(
            event=other_event,
            user=self.other_attendee,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], mine.id)
        self.assertEqual(response.data[0]["event"]["name"], "My event")

    def test_confirmed_and_cancelled_registrations_are_included(self):
        confirmed_event = self.make_event("Confirmed event")
        cancelled_event = self.make_event("Cancelled event")

        EventRegistration.objects.create(
            event=confirmed_event,
            user=self.attendee,
        )
        EventRegistration.objects.create(
            event=cancelled_event,
            user=self.attendee,
            status=EventRegistration.Status.CANCELLED,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {item["status"] for item in response.data},
            {"confirmed", "cancelled"},
        )

    def test_private_event_fields_are_not_exposed(self):
        event = self.make_event("Privacy test")
        EventRegistration.objects.create(
            event=event,
            user=self.attendee,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        event_data = response.data[0]["event"]

        for private_field in (
            "online_url",
            "joining_instructions",
            "organizer",
            "latitude",
            "longitude",
        ):
            self.assertNotIn(private_field, event_data)

    def test_empty_registration_history_returns_empty_list(self):
        self.client.force_authenticate(user=self.attendee)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_past_event_remains_in_registration_history(self):
        past_event = self.make_event(
            "Previous event",
            days_from_today=-3,
        )
        EventRegistration.objects.create(
            event=past_event,
            user=self.attendee,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["event"]["name"],
            "Previous event",
        )
