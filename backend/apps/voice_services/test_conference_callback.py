"""Security tests for the private conference callback."""

from django.test import TestCase
from django.urls import reverse


class ConferenceCallbackTests(TestCase):

    def setUp(self):
        self.url = reverse("conference-callback")

    def test_post_is_rejected_until_authentication_is_ready(self):
        response = self.client.post(
            self.url,
            {
                "sessionId": "unverified-call",
                "dtmfDigits": "12345678",
            },
        )

        self.assertEqual(response.status_code, 503)

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_callback_does_not_expose_conference_xml(self):
        response = self.client.post(
            self.url,
            {"sessionId": "unverified-call"},
        )

        self.assertNotIn(
            b"<Conference",
            response.content,
        )
