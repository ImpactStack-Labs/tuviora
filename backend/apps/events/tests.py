from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event


User = get_user_model()


class EventAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="organizer",
            password="test-password-123",
        )

        self.other_user = User.objects.create_user(
            username="other-organizer",
            password="test-password-123",
        )

        self.url = reverse("event-list-create")

        self.event_data = {
            "name": "Tuviora Hackathon",
            "category": "hackathon",
            "description": "An event operations hackathon.",
            "date": date.today() + timedelta(days=30),
            "start_time": time(9, 0),
            "end_time": time(17, 0),
            "event_format": "physical",
            "venue": "Uganda Christian University",
            "landmark": "Mukono",
            "latitude": 0.3536,
            "longitude": 32.7553,
            "capacity": 100,
        }

    def test_unauthenticated_user_cannot_access_events(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_authenticated_user_can_create_event(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            self.event_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        event = Event.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            event.organizer,
            self.user,
        )

        self.assertEqual(
            event.status,
            Event.Status.DRAFT,
        )

    def test_organizer_is_assigned_from_authenticated_user(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "organizer": self.other_user.id,
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        event = Event.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            event.organizer,
            self.user,
        )

    def test_user_only_sees_their_own_events(self):
        own_event = Event.objects.create(
        organizer=self.user,
        **self.event_data,
        )

        other_event_data = {
        **self.event_data,
        "name": "Another Organizer Event",
      }

        Event.objects.create(
        organizer=self.other_user,
        **other_event_data,
    )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
    )

        self.assertEqual(
        len(response.data),
        1,
    )

        self.assertEqual(
        response.data[0]["id"],
        own_event.id,
    )

    
    def test_event_defaults_to_draft(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            self.event_data,
            format="json",
        )

        self.assertEqual(
            response.data["status"],
            "draft",
        )

    def test_physical_event_requires_venue(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "venue": "",
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("venue", response.data)

    def test_virtual_event_requires_online_details(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "event_format": "virtual",
            "venue": "",
            "online_platform": "",
            "online_url": "",
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "online_platform",
            response.data,
        )

    def test_virtual_event_can_be_created(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "event_format": "virtual",
            "venue": "",
            "landmark": "",
            "latitude": None,
            "longitude": None,
            "online_platform": "Zoom",
            "online_url": "https://zoom.us/j/123456789",
            "joining_instructions": "Join using the event link.",
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_hybrid_event_requires_online_details(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "event_format": "hybrid",
            "online_platform": "",
            "online_url": "",
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "online_platform",
            response.data,
        )

    def test_end_time_must_be_after_start_time(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "start_time": "17:00:00",
            "end_time": "09:00:00",
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "end_time",
            response.data,
        )

    def test_past_event_date_is_rejected(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "date": date.today() - timedelta(days=1),
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "date",
            response.data,
        )

    def test_capacity_must_be_positive(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "capacity": 0,
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_coordinates_must_be_provided_together(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "latitude": 0.3536,
            "longitude": None,
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "latitude",
            response.data,
        )

    def test_invalid_online_url_is_rejected(self):
        self.client.force_authenticate(user=self.user)

        data = {
            **self.event_data,
            "event_format": "virtual",
            "venue": "",
            "online_platform": "Zoom",
            "online_url": "not-a-valid-url",
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "online_url",
            response.data,
        )