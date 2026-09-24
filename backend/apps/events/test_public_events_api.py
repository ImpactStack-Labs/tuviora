from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import Event, TicketType


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


class PublicEventDetailTests(TestCase):
    """Verify public event details and their visibility restrictions."""

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

    def test_anonymous_visitor_can_open_published_event_detail(self):
        event = self.make_event(
            "Public event detail",
            status=Event.Status.PUBLISHED,
            days_from_today=2,
        )

        response = self.client.get(
            reverse("public-event-detail", kwargs={"pk": event.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], event.pk)
        self.assertEqual(response.data["name"], event.name)

    def test_unpublished_and_past_event_details_return_404(self):
        for status, days in (
            (Event.Status.DRAFT, 2),
            (Event.Status.CANCELLED, 2),
            (Event.Status.COMPLETED, 2),
            (Event.Status.PUBLISHED, -2),
        ):
            with self.subTest(status=status, days=days):
                event = self.make_event(
                    f"Restricted {status} {days}",
                    status=status,
                    days_from_today=days,
                )

                response = self.client.get(
                    reverse("public-event-detail", kwargs={"pk": event.pk})
                )

                self.assertEqual(response.status_code, 404)

    def test_public_detail_does_not_expose_private_information(self):
        event = self.make_event(
            "Privacy test",
            status=Event.Status.PUBLISHED,
            days_from_today=1,
        )

        response = self.client.get(
            reverse("public-event-detail", kwargs={"pk": event.pk})
        )

        self.assertEqual(response.status_code, 200)

        for private_field in (
            "online_url",
            "joining_instructions",
            "organizer",
            "latitude",
            "longitude",
        ):
            self.assertNotIn(private_field, response.data)

    def test_unknown_event_returns_404(self):
        response = self.client.get(
            reverse("public-event-detail", kwargs={"pk": 999999})
        )

        self.assertEqual(response.status_code, 404)


class PublicEventTicketTypesTests(APITestCase):
    def setUp(self):
        self.organizer = get_user_model().objects.create_user(
            username="public_ticket_organizer",
            password="TestPassword123!",
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Public Ticket Test",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        TicketType.objects.create(
            event=self.event, name="Standard", price="25000.00"
        )
        TicketType.objects.create(
            event=self.event,
            name="Retired",
            price="10000.00",
            is_active=False,
        )

    def test_public_event_only_lists_active_ticket_types(self):
        response = self.client.get(f"/api/events/public/{self.event.id}/")
        names = [t["name"] for t in response.data["ticket_types"]]
        self.assertEqual(names, ["Standard"])

    def test_public_event_list_does_not_n_plus_one_on_ticket_types(self):
        # A small event count (e.g. 3) doesn't push the query count
        # past the threshold even when broken, so use enough events
        # that an unprefetched per-event query is unambiguously caught.
        for i in range(12):
            event = Event.objects.create(
                organizer=self.organizer,
                name=f"N+1 Test Event {i}",
                category=Event.Category.CONFERENCE,
                date=timezone.localdate() + timedelta(days=7),
                start_time="09:00",
                end_time="17:00",
                venue="Kampala",
                status=Event.Status.PUBLISHED,
            )
            TicketType.objects.create(
                event=event, name="Standard", price="10000.00"
            )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/events/public/")

        self.assertEqual(response.status_code, 200)
        # However many queries the endpoint takes, it must not scale
        # with the number of events (that's the N+1 signature).
        query_count = len(ctx.captured_queries)
        self.assertLess(
            query_count, 10,
            f"Expected a small constant number of queries, got {query_count}. "
            "ticket_types may not be prefetched.",
        )
