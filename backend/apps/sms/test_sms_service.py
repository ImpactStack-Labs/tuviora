"""Tests for Tuviora's reusable Africa's Talking SMS service."""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.sms.services.sms_service import (
    SMSServiceError,
    send_sms,
    validate_phone_number,
)


@override_settings(
    SMS_ENABLED=True,
    AFRICASTALKING_USERNAME="sandbox",
    AFRICASTALKING_API_KEY="test-api-key",
    AFRICASTALKING_SENDER_ID="",
)
class SMSServiceTests(SimpleTestCase):

    def test_valid_ugandan_phone_number(self):
        self.assertEqual(
            validate_phone_number("+256700123456"),
            "+256700123456",
        )

    def test_valid_international_phone_number(self):
        self.assertEqual(
            validate_phone_number("+254712345678"),
            "+254712345678",
        )

    def test_phone_number_whitespace_is_removed(self):
        self.assertEqual(
            validate_phone_number(" +256700123456 "),
            "+256700123456",
        )

    def test_invalid_phone_numbers_are_rejected(self):
        invalid_numbers = [
            "0700123456",
            "256700123456",
            "+256 700 123456",
            "+0123456789",
            "",
            None,
        ]

        for number in invalid_numbers:
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    validate_phone_number(number)

    @patch("apps.sms.services.sms_service.africastalking")
    def test_successful_sms_submission(self, mock_at):
        mock_at.SMS.send.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {
                        "number": "+256700123456",
                        "status": "Success",
                        "messageId": "test-message-id",
                    }
                ]
            }
        }

        response = send_sms(
            "+256700123456",
            "Welcome to Tuviora!",
        )

        mock_at.initialize.assert_called_once_with(
            "sandbox",
            "test-api-key",
        )

        mock_at.SMS.send.assert_called_once_with(
            message="Welcome to Tuviora!",
            recipients=["+256700123456"],
        )

        self.assertEqual(
            response["SMSMessageData"]["Recipients"][0]["status"],
            "Success",
        )

    @patch("apps.sms.services.sms_service.africastalking")
    def test_rejected_sms_raises_error(self, mock_at):
        mock_at.SMS.send.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {
                        "number": "+256700123456",
                        "status": "InvalidPhoneNumber",
                    }
                ]
            }
        }

        with self.assertRaises(SMSServiceError):
            send_sms("+256700123456", "Test message")

    @patch("apps.sms.services.sms_service.africastalking")
    def test_empty_provider_response_raises_error(self, mock_at):
        mock_at.SMS.send.return_value = {
            "SMSMessageData": {"Recipients": []}
        }

        with self.assertRaises(SMSServiceError):
            send_sms("+256700123456", "Test message")

    @patch("apps.sms.services.sms_service.africastalking")
    def test_api_failure_raises_error(self, mock_at):
        mock_at.SMS.send.side_effect = ConnectionError(
            "Simulated provider failure"
        )

        with self.assertRaises(SMSServiceError):
            send_sms("+256700123456", "Test message")

    @patch("apps.sms.services.sms_service.africastalking")
    def test_empty_message_is_rejected(self, mock_at):
        with self.assertRaises(ValueError):
            send_sms("+256700123456", "   ")

        mock_at.SMS.send.assert_not_called()

    @override_settings(AFRICASTALKING_API_KEY="")
    @patch("apps.sms.services.sms_service.africastalking")
    def test_missing_credentials(self, mock_at):
        with self.assertRaises(SMSServiceError):
            send_sms("+256700123456", "Test message")

        mock_at.initialize.assert_not_called()
