"""Tests for Africa's Talking conference XML."""

from xml.etree import ElementTree

from django.test import SimpleTestCase, override_settings

from .conference_xml import conference_response


@override_settings(VOICE_CONFERENCE_MAX_PARTICIPANTS=20)
class ConferenceXMLTests(SimpleTestCase):

    def parse_conference(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/xml",
        )

        root = ElementTree.fromstring(response.content)
        self.assertEqual(root.tag, "Response")

        conference = root.find("Conference")
        self.assertIsNotNone(conference)

        return conference

    def test_organizer_is_moderator(self):
        response = conference_response(
            "tuviora_event_123",
            is_organizer=True,
        )

        conference = self.parse_conference(response)

        self.assertEqual(
            conference.text,
            "tuviora_event_123",
        )
        self.assertEqual(
            conference.attrib["flags"],
            "moderator",
        )
        self.assertEqual(
            conference.attrib["startOnEnter"],
            "true",
        )
        self.assertEqual(
            conference.attrib["endOnExit"],
            "true",
        )
        self.assertEqual(
            conference.attrib["record"],
            "false",
        )

    def test_worker_joins_without_moderator_controls(self):
        response = conference_response(
            "tuviora_event_123",
            is_organizer=False,
        )

        conference = self.parse_conference(response)

        self.assertEqual(
            conference.attrib["flags"],
            "joinOnly",
        )
        self.assertEqual(
            conference.attrib["startOnEnter"],
            "false",
        )
        self.assertEqual(
            conference.attrib["endOnExit"],
            "false",
        )
        self.assertEqual(
            conference.attrib["maxParticipants"],
            "20",
        )

    def test_invalid_room_name_is_rejected(self):
        with self.assertRaises(ValueError):
            conference_response("../another_room")

    @override_settings(VOICE_CONFERENCE_MAX_PARTICIPANTS=51)
    def test_excessive_participant_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            conference_response("tuviora_event_123")
