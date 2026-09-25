import uuid
from datetime import date, time

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import (
    Event,
    EventMembership,
    EventRegistration,
    RegistrationTicket,
)


class TicketCheckInTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="checkin_organizer",
            password="TestPass123!",
        )
        self.staff = User.objects.create_user(
            username="checkin_staff",
            password="TestPass123!",
        )
        self.attendee = User.objects.create_user(
            username="checkin_attendee",
            password="TestPass123!",
        )
        self.outsider = User.objects.create_user(
            username="checkin_outsider",
            password="TestPass123!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Check-in Test Event",
            category=Event.Category.HACKATHON,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
            status=Event.Status.PUBLISHED,
        )

        EventMembership.objects.create(
            event=self.event,
            user=self.staff,
            role=EventMembership.Role.MEMBER,
        )

        self.registration = EventRegistration.objects.create(
            event=self.event,
            user=self.attendee,
            status=EventRegistration.Status.CONFIRMED,
        )

        self.ticket = RegistrationTicket.objects.create(
            registration=self.registration,
        )

        self.url = reverse(
            "event-ticket-check-in",
            kwargs={"event_id": self.event.pk},
        )

    def check_in(self, user, token=None):
        self.client.force_authenticate(user=user)
        return self.client.post(
            self.url,
            {"token": str(token or self.ticket.qr_token)},
            format="json",
        )

    def test_organizer_can_check_in_attendee(self):
        response = self.check_in(self.organizer)

        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.checked_in_at)
        self.assertEqual(self.ticket.checked_in_by, self.organizer)

    def test_team_member_can_check_in_attendee(self):
        response = self.check_in(self.staff)

        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.checked_in_by, self.staff)

    def test_ticket_reference_can_be_used(self):
        response = self.check_in(
            self.organizer,
            token=self.ticket.reference,
        )

        self.assertEqual(response.status_code, 200)

    def test_duplicate_check_in_is_rejected(self):
        first = self.check_in(self.organizer)
        second = self.check_in(self.staff)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)

    def test_outsider_cannot_check_in(self):
        response = self.check_in(self.outsider)

        self.assertEqual(response.status_code, 403)
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.checked_in_at)

    def test_invalid_ticket_is_rejected(self):
        response = self.check_in(
            self.organizer,
            token=uuid.uuid4(),
        )

        self.assertEqual(response.status_code, 404)

    def test_payment_pending_registration_is_rejected(self):
        self.registration.status = EventRegistration.Status.PAYMENT_PENDING
        self.registration.save(update_fields=["status"])

        response = self.check_in(self.organizer)

        self.assertEqual(response.status_code, 403)

    def test_cancelled_registration_is_rejected(self):
        self.registration.status = EventRegistration.Status.CANCELLED
        self.registration.save(update_fields=["status"])

        response = self.check_in(self.organizer)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_check_in(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.url,
            {"token": str(self.ticket.qr_token)},
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))

    def test_other_event_cannot_use_ticket(self):
        other_event = Event.objects.create(
            organizer=self.organizer,
            name="Other Check-in Event",
            category=Event.Category.WORKSHOP,
            date=date(2026, 9, 27),
            start_time=time(9, 0),
            end_time=time(17, 0),
            status=Event.Status.PUBLISHED,
        )

        self.client.force_authenticate(user=self.organizer)

        response = self.client.post(
            reverse(
                "event-ticket-check-in",
                kwargs={"event_id": other_event.pk},
            ),
            {"token": str(self.ticket.qr_token)},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
