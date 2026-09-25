"""Tests for the team SMS messaging endpoint."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sms.models import SMSPreference

from .models import Event, EventMembership


class MessageTeamAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="msg_team_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="msg_team_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="msg_team_member",
            password="TestPassword2026!",
        )
        self.outsider = User.objects.create_user(
            username="msg_team_outsider",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Message Team Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 5),
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

        self.url = reverse(
            "event-team-message",
            kwargs={"event_id": self.event.id},
        )

    @patch("apps.events.team_views.send_team_sms")
    def test_organizer_can_message_team(self, mock_send):
        mock_send.return_value = {
            "submitted": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.url,
            {"message": "All hands on deck"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["submitted"], 2)
        mock_send.assert_called_once_with(
            self.event,
            "All hands on deck",
        )

    @patch("apps.events.team_views.send_team_sms")
    def test_manager_can_message_team(self, mock_send):
        mock_send.return_value = {
            "submitted": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            self.url,
            {"message": "Doors open at 8am"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_member_cannot_message_team(self):
        self.client.force_authenticate(self.member)

        response = self.client.post(
            self.url,
            {"message": "Hello"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_gets_not_found(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.post(
            self.url,
            {"message": "Hello"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_blank_message_is_rejected(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(self.url, {"message": "   "})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_overlong_message_is_rejected(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.url,
            {"message": "x" * 481},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch("apps.sms.services.event_sms_notifications.send_sms")
    def test_organizer_can_message_team_end_to_end(self, mock_send_sms):
        SMSPreference.objects.create(
            user=self.organizer,
            phone_number="+256700000009",
            sms_enabled=True,
        )
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.url,
            {"message": "All hands on deck"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"submitted": 1, "failed": 0, "skipped": 2},
        )
        mock_send_sms.assert_called_once_with(
            "+256700000009",
            "All hands on deck",
        )
