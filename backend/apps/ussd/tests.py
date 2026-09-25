from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.sms.models import SMSPreference
from apps.events.models import Event, EventRegistration, TicketType


class USSDCallbackTests(TestCase):
    def setUp(self):
        self.url = reverse("ussd-callback")
        self.payload = {
            "sessionId": "test-session-1",
            "serviceCode": "*384*123#",
            "phoneNumber": "+256712345678",
            "text": "",
        }

    def send(self, text, **changes):
        return self.client.post(
            self.url,
            {**self.payload, "text": text, **changes},
        )

    def test_main_menu_uses_con(self):
        response = self.send("")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.decode().startswith("CON "))
        self.assertIn("1. Event information", response.content.decode())

    def test_event_prompt_uses_con(self):
        response = self.send("1")
        self.assertIn("CON Enter the published event ID", response.content.decode())

    def test_published_event_information_uses_end(self):
        organizer = get_user_model().objects.create_user(username="organizer")
        event = Event.objects.create(
            organizer=organizer,
            name="Tuviora Summit",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )

        response = self.send(f"1*{event.pk}")
        self.assertTrue(response.content.decode().startswith("END "))
        self.assertIn("Tuviora Summit", response.content.decode())

    def test_unknown_event_is_not_disclosed(self):
        response = self.send("1*999999")
        self.assertEqual(response.content.decode(), "END Published event not found.")

    def test_registration_prompt_uses_con(self):
        response = self.send("2")
        self.assertIn("CON Enter the event ID", response.content.decode())

    def test_registration_details_for_linked_phone(self):
        organizer = get_user_model().objects.create_user(username="organizer")
        attendee = get_user_model().objects.create_user(username="attendee")
        SMSPreference.objects.create(
            user=attendee,
            phone_number="+256712345678",
            sms_enabled=False,
        )
        event = Event.objects.create(
            organizer=organizer,
            name="Tuviora Summit",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        ticket_type = TicketType.objects.create(
            event=event, name="VIP", price=50000, currency="UGX"
        )
        EventRegistration.objects.create(
            event=event,
            user=attendee,
            ticket_type=ticket_type,
            amount_due=50000,
            currency="UGX",
            status=EventRegistration.Status.CONFIRMED,
        )

        response = self.send(f"2*{event.pk}")
        body = response.content.decode()
        self.assertTrue(body.startswith("END "))
        self.assertIn("Tuviora Summit", body)
        self.assertIn("Confirmed", body)
        self.assertIn("VIP ticket", body)
        self.assertIn("50000.00 UGX due", body)

    def test_registration_not_found_for_unlinked_phone(self):
        organizer = get_user_model().objects.create_user(username="organizer")
        event = Event.objects.create(
            organizer=organizer,
            name="Tuviora Summit",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )

        response = self.send(f"2*{event.pk}")
        self.assertEqual(
            response.content.decode(),
            "END No registration found for this event.",
        )

    def test_registration_not_found_for_other_event(self):
        organizer = get_user_model().objects.create_user(username="organizer")
        attendee = get_user_model().objects.create_user(username="attendee")
        SMSPreference.objects.create(
            user=attendee, phone_number="+256712345678", sms_enabled=False
        )
        registered_event = Event.objects.create(
            organizer=organizer,
            name="Tuviora Summit",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
            status=Event.Status.PUBLISHED,
        )
        other_event = Event.objects.create(
            organizer=organizer,
            name="Tech Meetup",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 1),
            start_time=time(9, 0),
            end_time=time(17, 0),
            status=Event.Status.PUBLISHED,
        )
        EventRegistration.objects.create(event=registered_event, user=attendee)

        response = self.send(f"2*{other_event.pk}")
        self.assertEqual(
            response.content.decode(),
            "END No registration found for this event.",
        )

    def test_invalid_registration_event_id(self):
        response = self.send("2*abc")
        self.assertEqual(
            response.content.decode(),
            "END Invalid event ID. Please dial again.",
        )

    def test_invalid_menu_choice(self):
        response = self.send("8")
        self.assertTrue(response.content.decode().startswith("CON Invalid choice."))

    def test_invalid_phone_ends_session(self):
        response = self.send("", phoneNumber="invalid")
        self.assertTrue(response.content.decode().startswith("END "))

    def test_exit_after_invalid_choice_uses_end(self):
        response = self.send("8*0")
        self.assertEqual(
            response.content.decode(),
            "END Thank you for using Tuviora.",
        )

    def test_exit_uses_end(self):
        response = self.send("0")
        self.assertEqual(
            response.content.decode(),
            "END Thank you for using Tuviora.",
        )

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
