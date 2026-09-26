"""Tests for outbound Africa's Talking voice call placement."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from .outbound_call_service import VoiceCallError, place_call


@override_settings(
    AT_VOICE_USERNAME="live_app",
    AT_VOICE_API_KEY="test-key",
    AT_VOICE_NUMBER="+256711000000",
)
class PlaceCallTests(TestCase):
    @patch("apps.voice_services.outbound_call_service.africastalking")
    def test_places_call_with_configured_number(self, mock_sdk):
        mock_sdk.VoiceService.return_value.call.return_value = {
            "entries": [
                {
                    "phoneNumber": "+256700000001",
                    "sessionId": "ATVId_test",
                    "status": "Queued",
                }
            ],
            "errorMessage": "None",
        }

        place_call("+256700000001")

        mock_sdk.VoiceService.assert_called_once_with(
            "live_app", "test-key",
        )
        mock_sdk.initialize.assert_not_called()
        mock_sdk.VoiceService.return_value.call.assert_called_once_with(
            "+256711000000", ["+256700000001"],
        )

    @patch("apps.voice_services.outbound_call_service.africastalking")
    def test_rejected_call_raises_voice_call_error(self, mock_sdk):
        mock_sdk.VoiceService.return_value.call.return_value = {
            "entries": [
                {
                    "phoneNumber": "+256700000001",
                    "sessionId": "ATVId_test",
                    "status": "InvalidPhoneNumber",
                }
            ],
            "errorMessage": "None",
        }

        with self.assertRaises(VoiceCallError):
            place_call("+256700000001")

    @patch("apps.voice_services.outbound_call_service.africastalking")
    def test_provider_error_raises_voice_call_error(self, mock_sdk):
        mock_sdk.VoiceService.return_value.call.side_effect = Exception("boom")

        with self.assertRaises(VoiceCallError):
            place_call("+256700000001")

    @override_settings(AT_VOICE_NUMBER="")
    def test_missing_configuration_raises_voice_call_error(self):
        with self.assertRaises(VoiceCallError):
            place_call("+256700000001")
