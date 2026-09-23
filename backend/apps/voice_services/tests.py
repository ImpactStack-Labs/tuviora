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

    def create_event(self, status="published"):
        from datetime import date, time
        from django.contrib.auth import get_user_model
        from apps.events.models import Event

        user = get_user_model().objects.create_user(
            username=f"organizer_{status}",
            password="test-password",
        )

        return Event.objects.create(
            organizer=user,
            name="Tuviora Community Festival",
            category=Event.Category.COMMUNITY,
            description="A community celebration.",
            date=date(2026, 9, 26),
            start_time=time(10, 0),
            end_time=time(17, 0),
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
            status=status,
        )

    def test_event_information(self):
        event = self.create_event()

        self.call()
        self.call("1")

        prompt = self.call("1")
        self.assertIn("event ID", self.message(prompt))

        response = self.call(str(event.pk))

        self.assertIn(
            "Tuviora Community Festival",
            self.message(response),
        )
        self.assertIn("26 September 2026", self.message(response))

    def test_draft_event_is_not_public(self):
        event = self.create_event(status="draft")

        self.call()
        self.call("1")
        self.call("1")

        response = self.call(str(event.pk))

        self.assertIn(
            "could not find",
            self.message(response),
        )

    def test_event_id_nine(self):
        from apps.events.models import Event

        event = self.create_event()
        Event.objects.filter(pk=event.pk).update(id=9)

        self.call()
        self.call("1")
        self.call("1")

        response = self.call("9")

        self.assertIn(
            "Tuviora Community Festival",
            self.message(response),
        )

    def test_star_returns_from_event_id_prompt(self):
        self.call()
        self.call("1")
        self.call("1")

        response = self.call("*")

        self.assertIn(
            "For event information",
            self.message(response),
        )

    def test_invalid_event_id(self):
        self.call()
        self.call("1")
        self.call("1")

        response = self.call("999999")

        self.assertIn(
            "could not find",
            self.message(response),
        )

    def test_swahili_event_information(self):
        event = self.create_event()

        self.call()
        self.call("2")
        self.call("1")

        response = self.call(str(event.pk))

        self.assertIn(
            "Tukio la Tuviora Community Festival",
            self.message(response),
        )

    def test_luganda_event_information(self):
        event = self.create_event()

        self.call()
        self.call("3")
        self.call("1")

        response = self.call(str(event.pk))

        self.assertIn(
            "Omukolo gwa Tuviora Community Festival",
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
