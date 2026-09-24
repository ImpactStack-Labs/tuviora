"""Tests for authenticated conference access-code issuance."""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.events.models import Event, EventMembership

from .conference_service import end_conference, start_conference
from .models import ConferenceAccessCode


@override_settings(VOICE_CONFERENCE_ENABLED=True)
class ConferenceAccessCodeAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="pin_organizer",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="pin_manager",
            password="test-password",
        )
        self.worker = User.objects.create_user(
            username="pin_worker",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="pin_outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="PIN API Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        EventMembership.objects.create(
            event=self.event,
            user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.event,
            user=self.worker,
            role=EventMembership.Role.MEMBER,
        )

        self.conference = start_conference(
            self.event,
            self.organizer,
        )

        self.url = reverse(
            "event-conference-access-code",
            kwargs={"event_id": self.event.pk},
        )

    def request_code(self, user):
        self.client.force_authenticate(user=user)
        return self.client.post(self.url)

    def test_organizer_can_request_code(self):
        response = self.request_code(self.organizer)

        self.assertEqual(response.status_code, 201)
        self.assertRegex(
            response.data["access_code"],
            r"^[0-9]{8}$",
        )
        self.assertEqual(
            response.data["expires_in_seconds"],
            600,
        )

    def test_manager_can_request_code(self):
        response = self.request_code(self.manager)
        self.assertEqual(response.status_code, 201)

    def test_worker_can_request_code(self):
        response = self.request_code(self.worker)
        self.assertEqual(response.status_code, 201)

    def test_outsider_cannot_request_code(self):
        response = self.request_code(self.outsider)
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_request_code(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url)

        self.assertIn(response.status_code, (401, 403))

    @override_settings(VOICE_CONFERENCE_ENABLED=False)
    def test_disabled_feature_rejects_code_request(self):
        response = self.request_code(self.organizer)

        self.assertEqual(response.status_code, 503)
        self.assertFalse(
            ConferenceAccessCode.objects.exists()
        )

    def test_ended_conference_rejects_code_request(self):
        end_conference(self.event, self.organizer)

        response = self.request_code(self.worker)

        self.assertEqual(response.status_code, 409)

    def test_response_disables_caching(self):
        response = self.request_code(self.worker)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response["Cache-Control"],
            "no-store",
        )

    def test_second_code_invalidates_first(self):
        self.request_code(self.worker)
        second = self.request_code(self.worker)

        self.assertEqual(second.status_code, 201)
        self.assertEqual(
            ConferenceAccessCode.objects.filter(
                conference=self.conference,
                user=self.worker,
                used_at__isnull=True,
            ).count(),
            1,
        )
