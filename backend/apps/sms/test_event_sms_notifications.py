"""Tests for consent-aware event SMS notifications."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.sms.models import SMSPreference
from apps.sms.services.event_sms_notifications import send_attendee_sms
from apps.sms.services.sms_service import SMSServiceError


class EventSMSNotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.opted_in = User.objects.create_user(
            username="sms_opted_in",
            password="TestPassword2026!",
        )
        self.opted_out = User.objects.create_user(
            username="sms_opted_out",
            password="TestPassword2026!",
        )
        self.other = User.objects.create_user(
            username="sms_other",
            password="TestPassword2026!",
        )

        SMSPreference.objects.create(
            user=self.opted_in,
            phone_number="+256700123456",
            sms_enabled=True,
        )
        SMSPreference.objects.create(
            user=self.opted_out,
            phone_number="+256700123457",
            sms_enabled=False,
        )
        SMSPreference.objects.create(
            user=self.other,
            phone_number="+256700123458",
            sms_enabled=True,
        )

    @patch(
        "apps.sms.services.event_sms_notifications.send_sms"
    )
    def test_only_selected_opted_in_user_receives_sms(
        self,
        mock_send,
    ):
        result = send_attendee_sms(
            [self.opted_in.id, self.opted_out.id],
            "Your event starts tomorrow.",
        )

        mock_send.assert_called_once_with(
            "+256700123456",
            "Your event starts tomorrow.",
        )
        self.assertEqual(result["submitted"], 1)
        self.assertEqual(result["skipped"], 1)

    @patch(
        "apps.sms.services.event_sms_notifications.send_sms"
    )
    def test_unselected_user_receives_nothing(
        self,
        mock_send,
    ):
        send_attendee_sms(
            [self.opted_in.id],
            "Event update.",
        )

        self.assertEqual(mock_send.call_count, 1)
        self.assertNotEqual(
            mock_send.call_args.args[0],
            "+256700123458",
        )

    @patch(
        "apps.sms.services.event_sms_notifications.send_sms"
    )
    def test_provider_failure_is_recorded(
        self,
        mock_send,
    ):
        mock_send.side_effect = SMSServiceError(
            "Simulated provider failure"
        )

        result = send_attendee_sms(
            [self.opted_in.id],
            "Important update.",
        )

        self.assertEqual(result["submitted"], 0)
        self.assertEqual(result["failed"], 1)

    @patch(
        "apps.sms.services.event_sms_notifications.send_sms"
    )
    def test_no_consent_means_no_sms(
        self,
        mock_send,
    ):
        result = send_attendee_sms(
            [self.opted_out.id],
            "Event reminder.",
        )

        mock_send.assert_not_called()
        self.assertEqual(result["skipped"], 1)

    @patch(
        "apps.sms.services.event_sms_notifications.send_sms"
    )
    def test_empty_recipient_list_sends_nothing(
        self,
        mock_send,
    ):
        result = send_attendee_sms([], "Event update.")

        mock_send.assert_not_called()
        self.assertEqual(result["submitted"], 0)

    def test_empty_message_is_rejected(self):
        with self.assertRaises(ValueError):
            send_attendee_sms(
                [self.opted_in.id],
                "   ",
            )
