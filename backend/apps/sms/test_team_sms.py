"""Tests for team-wide SMS notifications."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.events.models import Event, EventMembership
from apps.sms.models import SMSPreference
from apps.sms.services.event_sms_notifications import send_team_sms


class SendTeamSMSTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="team_sms_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="team_sms_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="team_sms_member",
            password="TestPassword2026!",
        )
        self.outsider = User.objects.create_user(
            username="team_sms_outsider",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Team SMS Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 1),
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
            phone_number="+256700000001",
            sms_enabled=True,
        )
        SMSPreference.objects.create(
            user=self.manager,
            phone_number="+256700000002",
            sms_enabled=True,
        )
        SMSPreference.objects.create(
            user=self.member,
            phone_number="+256700000003",
            sms_enabled=True,
        )
        SMSPreference.objects.create(
            user=self.outsider,
            phone_number="+256700000004",
            sms_enabled=True,
        )

    @patch("apps.sms.services.event_sms_notifications.send_sms")
    def test_sends_to_organizer_and_all_members_only(self, mock_send_sms):
        result = send_team_sms(self.event, "Team update")

        called_numbers = {
            call.args[0] for call in mock_send_sms.call_args_list
        }

        self.assertEqual(
            called_numbers,
            {"+256700000001", "+256700000002", "+256700000003"},
        )
        self.assertEqual(
            result,
            {"submitted": 3, "failed": 0, "skipped": 0},
        )

    @patch("apps.sms.services.event_sms_notifications.send_sms")
    def test_does_not_message_users_outside_the_team(self, mock_send_sms):
        send_team_sms(self.event, "Team update")

        called_numbers = {
            call.args[0] for call in mock_send_sms.call_args_list
        }

        self.assertNotIn("+256700000004", called_numbers)
