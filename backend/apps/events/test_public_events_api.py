from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Event


class PublicEventListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.organizer = get_user_model().objects.create_user(
            username="public_event_organizer",
            password="test-password",
        )
        self.today = timezone.localdate()
        self.url = reverse("public-event-list")

    def make_event(self, name, *, status, days_from_today):
        return Event.objects.create(
            organizer=self.organizer,
            name=name,
            category=Event.Category.HACKATHON,
            description="A test event.",
            date=self.today + timedelta(days=days_from_today),
            start_time="09:00",
            end_time="17:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
            capacity=100,
            status=status,
            online_url="https://example.com/private-meeting",
            joining_instructions="Private instructions",
        )

    def test_anonymous_visitors_can_view_published_upcoming_events(self):
        event = self.make_event(
            "Upcoming hackathon",
            status=Event.Status.PUBLISHED,
            days_from_today=2,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], event.id)

    def test_unpublished_and_past_events_are_excluded(self):
        self.make_event(
            "Published upcoming",
            status=Event.Status.PUBLISHED,
            days_from_today=2,
        )
        self.make_event(
            "Draft upcoming",
            status=Event.Status.DRAFT,
            days_from_today=2,
        )
        self.make_event(
            "Cancelled upcoming",
            status=Event.Status.CANCELLED,
            days_from_today=2,
        )
        self.make_event(
            "Completed upcoming",
            status=Event.Status.COMPLETED,
            days_from_today=2,
        )
        self.make_event(
            "Published past",
            status=Event.Status.PUBLISHED,
            days_from_today=-2,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["name"] for item in response.data],
            ["Published upcoming"],
        )

    def test_private_event_information_is_not_exposed(self):
        self.make_event(
            "Public listing",
            status=Event.Status.PUBLISHED,
            days_from_today=1,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        event = response.data[0]

        for private_field in (
            "online_url",
            "joining_instructions",
            "organizer",
            "latitude",
            "longitude",
        ):
            self.assertNotIn(private_field, event)

    def test_events_are_ordered_by_date(self):
        self.make_event(
            "Later event",
            status=Event.Status.PUBLISHED,
            days_from_today=5,
        )
        self.make_event(
            "Earlier event",
            status=Event.Status.PUBLISHED,
            days_from_today=1,
        )

        response = self.client.get(self.url)

        self.assertEqual(
            [item["name"] for item in response.data],
            ["Earlier event", "Later event"],
        )
