from xml.etree import ElementTree

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class VoiceCallbackTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("voice-callback")
        self.session_id = "test-call-123"

    def call(self, digits=None):
        data = {"sessionId": self.session_id}

        if digits is not None:
            data["dtmfDigits"] = digits

        return self.client.post(self.url, data)

    def message(self, response):
        root = ElementTree.fromstring(response.content)
        return " ".join(
            node.text or ""
            for node in root.iter("Say")
        )

    def test_language_selection(self):
        response = self.call()

        self.assertEqual(response.status_code, 200)
        self.assertIn("English", self.message(response))
        self.assertIn("Kiswahili", self.message(response))

    def test_english_menu(self):
        self.call()

        response = self.call("1")

        self.assertIn(
            "For event information",
            self.message(response),
        )

    def test_swahili_menu(self):
        self.call()

        response = self.call("2")

        self.assertIn(
            "Kwa taarifa za tukio",
            self.message(response),
        )

    def test_luganda_menu(self):
        self.call()

        response = self.call("3")

        self.assertIn(
            "Okufuna amawulire",
            self.message(response),
        )

    def test_event_information(self):
        self.call()
        self.call("1")

        response = self.call("1")

        self.assertIn(
            "Event information will be available",
            self.message(response),
        )

    def test_return_to_main_menu(self):
        self.call()
        self.call("1")
        self.call("2")

        response = self.call("9")

        self.assertIn(
            "For event information",
            self.message(response),
        )

    def test_change_language(self):
        self.call()
        self.call("1")

        response = self.call("9")

        self.assertIn("Kiswahili", self.message(response))

    def test_invalid_language(self):
        self.call()

        response = self.call("8")

        self.assertIn(
            "Invalid language selection",
            self.message(response),
        )

    def test_end_call(self):
        self.call()
        self.call("1")

        response = self.call("0")

        root = ElementTree.fromstring(response.content)

        self.assertIsNotNone(root.find("Hangup"))

    def test_missing_session_id(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 400)
