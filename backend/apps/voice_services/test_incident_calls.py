"""Tests for critical-incident voice call escalation."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.events.models import Event, EventMembership, Incident
from apps.sms.models import SMSPreference

from .incident_calls import IncidentCallStateError, call_team_for_incident
from .models import PendingVoiceCall
from .outbound_call_service import VoiceCallError


class CallTeamForIncidentTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="incident_call_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="incident_call_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="incident_call_member",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Incident Call Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 10),
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

        SMSPreference.objects.create(
            user=self.organizer,
            phone_number="+256700000010",
            sms_enabled=False,
        )
        SMSPreference.objects.create(
            user=self.manager,
            phone_number="+256700000011",
            sms_enabled=False,
        )
        SMSPreference.objects.create(
            user=self.member,
            phone_number="+256700000012",
            sms_enabled=True,
        )

        self.incident = Incident.objects.create(
            event=self.event,
            title="Sound system failure",
            description="Main stage speakers are down.",
            category=Incident.Category.TECHNICAL,
            severity=Incident.Severity.CRITICAL,
        )

    def test_non_critical_incident_raises_state_error(self):
        self.incident.severity = Incident.Severity.HIGH
        self.incident.save(update_fields=["severity"])

        with self.assertRaises(IncidentCallStateError):
            call_team_for_incident(self.incident)

    @patch("apps.voice_services.incident_calls.place_call")
    def test_calls_organizer_and_managers_not_members(self, mock_place_call):
        call_team_for_incident(self.incident)

        called_numbers = {
            call.args[0] for call in mock_place_call.call_args_list
        }

        self.assertEqual(
            called_numbers,
            {"+256700000010", "+256700000011"},
        )

    @patch("apps.voice_services.incident_calls.place_call")
    def test_ignores_sms_enabled_flag(self, mock_place_call):
        # Both organizer and manager have sms_enabled=False above,
        # yet both must still be called.
        result = call_team_for_incident(self.incident)

        self.assertEqual(result["dialed"], 2)

    @patch("apps.voice_services.incident_calls.place_call")
    def test_recipient_without_phone_number_is_skipped(
        self, mock_place_call,
    ):
        SMSPreference.objects.filter(user=self.manager).delete()

        result = call_team_for_incident(self.incident)

        self.assertEqual(result["dialed"], 1)
        self.assertEqual(result["skipped"], 1)

    @patch("apps.voice_services.incident_calls.place_call")
    def test_creates_one_pending_call_row_per_dialed_recipient(
        self, mock_place_call,
    ):
        call_team_for_incident(self.incident)

        self.assertEqual(PendingVoiceCall.objects.count(), 2)
        pending_numbers = set(
            PendingVoiceCall.objects.values_list(
                "phone_number", flat=True,
            )
        )
        self.assertEqual(
            pending_numbers,
            {"+256700000010", "+256700000011"},
        )

    @patch("apps.voice_services.incident_calls.place_call")
    def test_provider_failure_is_counted_as_failed(self, mock_place_call):
        mock_place_call.side_effect = VoiceCallError("boom")

        result = call_team_for_incident(self.incident)

        self.assertEqual(result["dialed"], 0)
        self.assertEqual(result["failed"], 2)
