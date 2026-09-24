"""Tests for the Africa's Talking conference API client."""

from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from .conference_provider import (
    CONFERENCE_API_URL,
    ConferenceProviderError,
    send_conference_command,
)


@override_settings(
    AFRICASTALKING_USERNAME="test_user",
    AFRICASTALKING_API_KEY="test_api_key",
    AT_VOICE_NUMBER="+256700000000",
)
class ConferenceProviderTests(SimpleTestCase):

    @patch("apps.voice_services.conference_provider.requests.post")
    def test_successful_hangup(self, mock_post):
        response = Mock()
        response.json.return_value = {"status": True}
        mock_post.return_value = response

        result = send_conference_command(
            "tuviora_test_room",
            "hup",
            participant="all",
        )

        self.assertTrue(result["status"])

        mock_post.assert_called_once_with(
            CONFERENCE_API_URL,
            json={
                "username": "test_user",
                "phoneNumber": "+256700000000",
                "command": "hup",
                "roomName": "tuviora_test_room",
                "participant": "all",
            },
            headers={
                "apiKey": "test_api_key",
                "Accept": "application/json",
            },
            timeout=15,
        )

    @patch("apps.voice_services.conference_provider.requests.post")
    def test_successful_lock(self, mock_post):
        response = Mock()
        response.json.return_value = {"status": True}
        mock_post.return_value = response

        send_conference_command(
            "tuviora_test_room",
            "lock",
        )

        payload = mock_post.call_args.kwargs["json"]

        self.assertEqual(payload["command"], "lock")
        self.assertNotIn("participant", payload)

    @patch("apps.voice_services.conference_provider.requests.post")
    def test_rejected_provider_command(self, mock_post):
        response = Mock()
        response.json.return_value = {
            "status": False,
            "errorMessage": "Test rejection",
        }
        mock_post.return_value = response

        with self.assertRaises(ConferenceProviderError):
            send_conference_command(
                "tuviora_test_room",
                "hup",
                participant="all",
            )

    @patch("apps.voice_services.conference_provider.requests.post")
    def test_network_failure(self, mock_post):
        mock_post.side_effect = requests.Timeout()

        with self.assertRaises(ConferenceProviderError):
            send_conference_command(
                "tuviora_test_room",
                "hup",
                participant="all",
            )

    @patch("apps.voice_services.conference_provider.requests.post")
    def test_invalid_json(self, mock_post):
        response = Mock()
        response.json.side_effect = ValueError(
            "Invalid JSON"
        )
        mock_post.return_value = response

        with self.assertRaises(ConferenceProviderError):
            send_conference_command(
                "tuviora_test_room",
                "lock",
            )

    @patch("apps.voice_services.conference_provider.requests.post")
    def test_invalid_response_structure(self, mock_post):
        response = Mock()
        response.json.return_value = ["unexpected"]
        mock_post.return_value = response

        with self.assertRaises(ConferenceProviderError):
            send_conference_command(
                "tuviora_test_room",
                "lock",
            )

    @patch("apps.voice_services.conference_provider.requests.post")
    def test_unsupported_command_makes_no_request(
        self,
        mock_post,
    ):
        with self.assertRaises(ConferenceProviderError):
            send_conference_command(
                "tuviora_test_room",
                "delete",
            )

        mock_post.assert_not_called()

    @override_settings(
        AFRICASTALKING_API_KEY="",
    )
    @patch("apps.voice_services.conference_provider.requests.post")
    def test_missing_credentials_makes_no_request(
        self,
        mock_post,
    ):
        with self.assertRaises(ConferenceProviderError):
            send_conference_command(
                "tuviora_test_room",
                "lock",
            )

        mock_post.assert_not_called()
