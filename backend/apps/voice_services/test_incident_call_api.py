"""Tests for the critical-incident call-team endpoint."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventMembership, Incident


class IncidentCallTeamAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="call_api_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="call_api_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="call_api_member",
            password="TestPassword2026!",
        )
        self.outsider = User.objects.create_user(
            username="call_api_outsider",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Call API Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 12),
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
            user=self.member,
            role=EventMembership.Role.MEMBER,
        )

        self.critical_incident = Incident.objects.create(
            event=self.event,
            title="Power outage",
            description="Main venue lost power.",
            category=Incident.Category.POWER,
            severity=Incident.Severity.CRITICAL,
        )
        self.medium_incident = Incident.objects.create(
            event=self.event,
            title="Late vendor",
            description="Catering is running late.",
            category=Incident.Category.OTHER,
            severity=Incident.Severity.MEDIUM,
        )

        self.url = reverse(
            "event-incident-call-team",
            kwargs={
                "event_id": self.event.id,
                "incident_id": self.critical_incident.id,
            },
        )

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=False)
    def test_disabled_flag_returns_503(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    @patch("apps.voice_services.incident_call_views.call_team_for_incident")
    def test_organizer_can_call_team(self, mock_call):
        mock_call.return_value = {
            "dialed": 2, "failed": 0, "skipped": 0,
        }
        self.client.force_authenticate(self.organizer)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["dialed"], 2)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    @patch("apps.voice_services.incident_call_views.call_team_for_incident")
    def test_manager_can_call_team(self, mock_call):
        mock_call.return_value = {
            "dialed": 2, "failed": 0, "skipped": 0,
        }
        self.client.force_authenticate(self.manager)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    def test_member_gets_forbidden(self):
        self.client.force_authenticate(self.member)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    def test_outsider_gets_not_found(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    def test_non_critical_incident_returns_400(self):
        url = reverse(
            "event-incident-call-team",
            kwargs={
                "event_id": self.event.id,
                "incident_id": self.medium_incident.id,
            },
        )
        self.client.force_authenticate(self.organizer)

        response = self.client.post(url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST,
        )
