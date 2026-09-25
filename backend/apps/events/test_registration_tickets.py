from datetime import date, time

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Event, EventRegistration, RegistrationTicket


class RegistrationTicketTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="ticket_organizer",
            email="organizer-ticket@example.com",
            password="TestPass123!",
        )
        self.attendee = User.objects.create_user(
            username="ticket_attendee",
            email="attendee-ticket@example.com",
            password="TestPass123!",
        )
        self.other_user = User.objects.create_user(
            username="ticket_other",
            email="other-ticket@example.com",
            password="TestPass123!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Ticket Test Event",
            category=Event.Category.HACKATHON,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
            status=Event.Status.PUBLISHED,
        )

        self.registration = EventRegistration.objects.create(
            event=self.event,
            user=self.attendee,
            status=EventRegistration.Status.CONFIRMED,
        )

        self.url = reverse(
            "my-registration-ticket",
            kwargs={"event_id": self.event.pk},
        )

    def test_confirmed_attendee_receives_ticket(self):
        self.client.force_authenticate(user=self.attendee)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("reference", response.data)
        self.assertIn("qr_token", response.data)
        self.assertEqual(RegistrationTicket.objects.count(), 1)

    def test_repeated_requests_reuse_ticket(self):
        self.client.force_authenticate(user=self.attendee)

        first = self.client.get(self.url)
        second = self.client.get(self.url)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.data["qr_token"],
            second.data["qr_token"],
        )
        self.assertEqual(RegistrationTicket.objects.count(), 1)

    def test_payment_pending_cannot_receive_ticket(self):
        self.registration.status = EventRegistration.Status.PAYMENT_PENDING
        self.registration.save(update_fields=["status"])
        self.client.force_authenticate(user=self.attendee)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(RegistrationTicket.objects.exists())

    def test_cancelled_registration_cannot_receive_ticket(self):
        self.registration.status = EventRegistration.Status.CANCELLED
        self.registration.save(update_fields=["status"])
        self.client.force_authenticate(user=self.attendee)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(RegistrationTicket.objects.exists())

    def test_other_user_cannot_access_ticket(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(RegistrationTicket.objects.exists())

    def test_anonymous_user_cannot_access_ticket(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(RegistrationTicket.objects.exists())
