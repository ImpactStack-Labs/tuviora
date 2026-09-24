"""Tests for provider-aware conference management."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.events.models import Event

from .conference_provider import ConferenceProviderError
from .conference_service import (
    ConferencePermissionError,
    end_conference,
    start_conference,
)
from .models import EventConference


class ConferenceProviderServiceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="provider_service_organizer",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="provider_service_outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Provider Service Test",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        self.conference = start_conference(
            self.event,
            self.organizer,
        )

    @patch(
        "apps.voice_services.conference_service."
        "send_conference_command"
    )
    def test_successful_provider_hangup_ends_conference(
        self,
        mock_command,
    ):
        mock_command.return_value = {"status": True}

        conference = end_conference(
            self.event,
            self.organizer,
            notify_provider=True,
        )

        mock_command.assert_called_once_with(
            self.conference.room_name,
            "hup",
            participant="all",
        )

        self.assertEqual(
            conference.status,
            EventConference.Status.ENDED,
        )
        self.assertIsNotNone(conference.ended_at)

    @patch(
        "apps.voice_services.conference_service."
        "send_conference_command"
    )
    def test_provider_failure_keeps_conference_active(
        self,
        mock_command,
    ):
        mock_command.side_effect = ConferenceProviderError(
            "Provider unavailable."
        )

        with self.assertRaises(ConferenceProviderError):
            end_conference(
                self.event,
                self.organizer,
                notify_provider=True,
            )

        self.conference.refresh_from_db()

        self.assertEqual(
            self.conference.status,
            EventConference.Status.ACTIVE,
        )
        self.assertIsNone(self.conference.ended_at)

    @patch(
        "apps.voice_services.conference_service."
        "send_conference_command"
    )
    def test_outsider_cannot_trigger_provider_hangup(
        self,
        mock_command,
    ):
        with self.assertRaises(ConferencePermissionError):
            end_conference(
                self.event,
                self.outsider,
                notify_provider=True,
            )

        mock_command.assert_not_called()

        self.conference.refresh_from_db()
        self.assertEqual(
            self.conference.status,
            EventConference.Status.ACTIVE,
        )

    @patch(
        "apps.voice_services.conference_service."
        "send_conference_command"
    )
    def test_local_end_does_not_contact_provider(
        self,
        mock_command,
    ):
        conference = end_conference(
            self.event,
            self.organizer,
        )

        mock_command.assert_not_called()
        self.assertEqual(
            conference.status,
            EventConference.Status.ENDED,
        )
