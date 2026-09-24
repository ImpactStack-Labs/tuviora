"""Tests for MarzPay payment collection."""

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Event, EventRegistration, Payment, TicketType

User = get_user_model()


class PaymentModelTests(TestCase):
    def setUp(self):
        organizer = User.objects.create_user(
            username="payment_organizer", password="TestPassword123!"
        )
        attendee = User.objects.create_user(
            username="payment_attendee", password="TestPassword123!"
        )
        event = Event.objects.create(
            organizer=organizer,
            name="Tuviora Payment Test",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        ticket = TicketType.objects.create(
            event=event, name="Standard", price=Decimal("25000.00")
        )
        self.registration = EventRegistration.objects.create(
            event=event,
            user=attendee,
            ticket_type=ticket,
            amount_due=ticket.price,
            currency=ticket.currency,
            status=EventRegistration.Status.PAYMENT_PENDING,
        )

    def test_payment_defaults_to_pending(self):
        payment = Payment.objects.create(
            registration=self.registration,
            reference="11111111-1111-1111-1111-111111111111",
            method=Payment.Method.MOBILE_MONEY,
            phone_number="+256700123456",
            amount=self.registration.amount_due,
            currency=self.registration.currency,
        )
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_registration_can_have_multiple_payment_attempts(self):
        for i in range(2):
            Payment.objects.create(
                registration=self.registration,
                reference=f"2222222{i}-2222-2222-2222-222222222222",
                method=Payment.Method.MOBILE_MONEY,
                amount=self.registration.amount_due,
                currency=self.registration.currency,
            )
        self.assertEqual(self.registration.payments.count(), 2)
