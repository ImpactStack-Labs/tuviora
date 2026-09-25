"""Tests for the outbound-call branch of the voice callback."""

from xml.etree import ElementTree

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import PendingVoiceCall


class OutboundCallbackTests(TestCase):
    def setUp(self):
        self.url = reverse("voice-callback")

    def spoken_text(self, response):
        root = ElementTree.fromstring(response.content)
        return " ".join(
            node.text or "" for node in root.iter("Say")
        )

    def test_speaks_and_deletes_matching_pending_call(self):
        PendingVoiceCall.objects.create(
            phone_number="+256700000099",
            message="This is Tuviora. A critical incident...",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        response = self.client.post(
            self.url,
            {
                "sessionId": "outbound-session-1",
                "direction": "Outbound",
                "destinationNumber": "+256700000099",
            },
        )

        self.assertIn(
            "This is Tuviora. A critical incident...",
            self.spoken_text(response),
        )
        self.assertEqual(PendingVoiceCall.objects.count(), 0)

    def test_expired_pending_call_is_not_spoken(self):
        PendingVoiceCall.objects.create(
            phone_number="+256700000098",
            message="Stale message",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            self.url,
            {
                "sessionId": "outbound-session-2",
                "direction": "Outbound",
                "destinationNumber": "+256700000098",
            },
        )

        self.assertNotIn("Stale message", self.spoken_text(response))

    def test_no_matching_pending_call_does_not_crash(self):
        response = self.client.post(
            self.url,
            {
                "sessionId": "outbound-session-3",
                "direction": "Outbound",
                "destinationNumber": "+256700000097",
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_inbound_calls_are_unaffected(self):
        response = self.client.post(
            self.url,
            {"sessionId": "inbound-session-1"},
        )

        self.assertIn(
            "Welcome to Tuviora",
            self.spoken_text(response),
        )
