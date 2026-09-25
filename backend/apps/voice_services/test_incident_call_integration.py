"""Integration test across incident_calls -> PendingVoiceCall -> callback."""

from datetime import date, time
from unittest.mock import patch
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.events.models import Event, EventMembership, Incident
from apps.sms.models import SMSPreference

from .incident_calls import call_team_for_incident


class IncidentCallEndToEndTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="e2e_call_organizer",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="End To End Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 10),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        SMSPreference.objects.create(
            user=self.organizer,
            phone_number="+256700000050",
            sms_enabled=False,
        )

        self.incident = Incident.objects.create(
            event=self.event,
            title="Stage collapse",
            description="Main stage structure is unstable.",
            category=Incident.Category.VENUE,
            severity=Incident.Severity.CRITICAL,
        )

    @patch("apps.voice_services.incident_calls.place_call")
    def test_dialed_recipient_hears_the_stored_incident_message(
        self, mock_place_call,
    ):
        call_team_for_incident(self.incident)

        response = self.client.post(
            reverse("voice-callback"),
            {
                "sessionId": "e2e-session-1",
                "direction": "Outbound",
                "destinationNumber": "+256700000050",
                "isActive": "1",
            },
        )

        root = ElementTree.fromstring(response.content)
        spoken = " ".join(node.text or "" for node in root.iter("Say"))

        self.assertIn("End To End Event", spoken)
        self.assertIn("Stage collapse", spoken)
