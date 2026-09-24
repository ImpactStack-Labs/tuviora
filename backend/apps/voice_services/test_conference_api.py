"""Tests for authenticated event conference endpoints."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.events.models import Event, EventMembership

from .conference_provider import ConferenceProviderError
from .models import EventConference


@override_settings(VOICE_CONFERENCE_ENABLED=True)
class ConferenceAPITests(TestCase):

    def setUp(self):
        # No real provider requests are permitted during API tests.
        provider_patcher = patch(
            "apps.voice_services.conference_service."
            "send_conference_command",
            return_value={"status": True},
        )
        self.mock_provider = provider_patcher.start()
        self.addCleanup(provider_patcher.stop)

        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="api_organizer",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="api_manager",
            password="test-password",
        )
        self.worker = User.objects.create_user(
            username="api_worker",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="api_outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="API Conference Test",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        for user, role in (
            (self.manager, EventMembership.Role.MANAGER),
            (self.worker, EventMembership.Role.MEMBER),
        ):
            EventMembership.objects.create(
                event=self.event,
                user=user,
                role=role,
            )

        self.status_url = reverse(
            "event-conference-status",
            kwargs={"event_id": self.event.pk},
        )
        self.start_url = reverse(
            "event-conference-start",
            kwargs={"event_id": self.event.pk},
        )
        self.end_url = reverse(
            "event-conference-end",
            kwargs={"event_id": self.event.pk},
        )

        self.client = APIClient()

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_organizer_sees_not_started_status(self):
        self.authenticate(self.organizer)

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"],
            "not_started",
        )
        self.assertTrue(response.data["can_manage"])

    def test_worker_can_view_status(self):
        self.authenticate(self.worker)

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_manage"])

    def test_manager_can_view_status(self):
        self.authenticate(self.manager)

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_manage"])

    def test_organizer_can_start_conference(self):
        self.authenticate(self.organizer)

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"],
            EventConference.Status.ACTIVE,
        )
        self.assertEqual(
            EventConference.objects.filter(
                event=self.event,
            ).count(),
            1,
        )

    def test_worker_cannot_start_conference(self):
        self.authenticate(self.worker)

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            EventConference.objects.filter(
                event=self.event,
            ).exists()
        )

    def test_manager_cannot_end_conference(self):
        self.authenticate(self.organizer)
        self.client.post(self.start_url)

        self.authenticate(self.manager)
        response = self.client.post(self.end_url)

        self.assertEqual(response.status_code, 403)

        conference = EventConference.objects.get(
            event=self.event,
        )
        self.assertEqual(
            conference.status,
            EventConference.Status.ACTIVE,
        )

    def test_organizer_can_end_conference(self):
        self.authenticate(self.organizer)
        self.client.post(self.start_url)

        response = self.client.post(self.end_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"],
            EventConference.Status.ENDED,
        )

    def test_cannot_restart_ended_conference(self):
        self.authenticate(self.organizer)
        self.client.post(self.start_url)
        self.client.post(self.end_url)

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 409)

    def test_outsider_cannot_view_conference(self):
        self.authenticate(self.outsider)

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_view_conference(self):
        response = self.client.get(self.status_url)

        self.assertIn(response.status_code, (401, 403))

    def test_room_name_is_never_exposed(self):
        self.authenticate(self.organizer)
        start_response = self.client.post(self.start_url)
        status_response = self.client.get(self.status_url)

        self.assertNotIn(
            "room_name",
            start_response.data,
        )
        self.assertNotIn(
            "room_name",
            status_response.data,
        )

    @override_settings(VOICE_CONFERENCE_ENABLED=False)
    def test_disabled_start_returns_503(self):
        self.authenticate(self.organizer)

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 503)
        self.assertFalse(
            EventConference.objects.filter(
                event=self.event,
            ).exists()
        )
        self.mock_provider.assert_not_called()

    @override_settings(VOICE_CONFERENCE_ENABLED=False)
    def test_disabled_end_returns_503(self):
        self.authenticate(self.organizer)

        conference = EventConference.objects.create(
            event=self.event,
            organizer=self.organizer,
            room_name="tuviora_disabled_test_room",
            status=EventConference.Status.ACTIVE,
        )

        response = self.client.post(self.end_url)

        self.assertEqual(response.status_code, 503)
        conference.refresh_from_db()
        self.assertEqual(
            conference.status,
            EventConference.Status.ACTIVE,
        )
        self.mock_provider.assert_not_called()

    def test_provider_failure_returns_502_and_preserves_state(self):
        self.authenticate(self.organizer)
        start_response = self.client.post(self.start_url)
        self.assertEqual(start_response.status_code, 200)

        self.mock_provider.side_effect = ConferenceProviderError(
            "Provider unavailable."
        )

        response = self.client.post(self.end_url)

        self.assertEqual(response.status_code, 502)

        conference = EventConference.objects.get(
            event=self.event,
        )
        self.assertEqual(
            conference.status,
            EventConference.Status.ACTIVE,
        )
        self.assertIsNone(conference.ended_at)

    def test_ending_an_ended_conference_returns_409(self):
        self.authenticate(self.organizer)

        start_response = self.client.post(self.start_url)
        self.assertEqual(start_response.status_code, 200)

        first_end = self.client.post(self.end_url)
        self.assertEqual(first_end.status_code, 200)

        second_end = self.client.post(self.end_url)

        self.assertEqual(second_end.status_code, 409)
        self.assertEqual(
            self.mock_provider.call_count,
            1,
        )
