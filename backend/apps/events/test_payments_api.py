"""Tests for MarzPay payment collection."""

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventRegistration, Payment, TicketType
from .services.marzpay_service import MarzPayError

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


@override_settings(SMS_ENABLED=False)
class InitiatePaymentAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="init_payment_organizer",
            password="TestPassword123!",
        )
        self.attendee = User.objects.create_user(
            username="init_payment_attendee",
            password="TestPassword123!",
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Initiate Payment Test",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        self.ticket = TicketType.objects.create(
            event=self.event, name="Standard", price=Decimal("25000.00")
        )
        self.registration = EventRegistration.objects.create(
            event=self.event,
            user=self.attendee,
            ticket_type=self.ticket,
            amount_due=self.ticket.price,
            currency=self.ticket.currency,
            status=EventRegistration.Status.PAYMENT_PENDING,
        )
        self.pay_url = (
            f"/api/events/{self.event.id}/registrations/me/pay/"
        )
        self.client.force_authenticate(user=self.attendee)

    @patch("apps.events.payment_views.initiate_collection")
    def test_initiating_mobile_money_payment_creates_processing_payment(
        self, mock_initiate
    ):
        mock_initiate.return_value = {
            "transaction": {
                "uuid": "4e7fb3fa-c13a-4b05-8acd-cf60ff68cb94",
                "status": "processing",
            },
        }

        response = self.client.post(
            self.pay_url,
            {"method": "mobile_money", "phone_number": "+256700123456"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "processing")
        self.assertEqual(Payment.objects.count(), 1)
        mock_initiate.assert_called_once()

    def test_mobile_money_requires_a_valid_phone_number(self):
        response = self.client.post(
            self.pay_url,
            {"method": "mobile_money", "phone_number": "0700123456"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.events.payment_views.initiate_collection")
    def test_card_payment_returns_redirect_url(self, mock_initiate):
        mock_initiate.return_value = {
            "transaction": {"uuid": "abc", "status": "pending"},
            "redirect_url": "https://wallet.wearemarz.com/pay/card-gateway?x=1",
        }

        response = self.client.post(self.pay_url, {"method": "card"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["redirect_url"],
            "https://wallet.wearemarz.com/pay/card-gateway?x=1",
        )

    @patch("apps.events.payment_views.initiate_collection")
    def test_provider_failure_marks_payment_failed(self, mock_initiate):
        mock_initiate.side_effect = MarzPayError("Provider unavailable.")

        response = self.client.post(
            self.pay_url,
            {"method": "mobile_money", "phone_number": "+256700123456"},
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            Payment.objects.first().status, Payment.Status.FAILED
        )
        # The registration stays payment_pending so the attendee can retry.
        self.registration.refresh_from_db()
        self.assertEqual(
            self.registration.status,
            EventRegistration.Status.PAYMENT_PENDING,
        )

    def test_confirmed_registration_cannot_pay_again(self):
        self.registration.status = EventRegistration.Status.CONFIRMED
        self.registration.save(update_fields=["status"])

        response = self.client.post(
            self.pay_url,
            {"method": "mobile_money", "phone_number": "+256700123456"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.events.payment_views.initiate_collection")
    def test_initiate_payment_locks_the_registration_row(self, mock_initiate):
        # Regression test for the check-then-create race: two concurrent
        # POSTs could both read PAYMENT_PENDING before either created a
        # Payment, firing two MarzPay collections for one registration.
        # The test DB here is sqlite, which doesn't enforce row-level
        # locking (Django silently drops the FOR UPDATE clause), so a
        # genuine multi-threaded race can't be demonstrated reliably
        # against it. Instead we assert the view takes the lock at all,
        # by wrapping (not replacing) select_for_update so real behaviour
        # is preserved and we just observe that it was used.
        mock_initiate.return_value = {
            "transaction": {"uuid": "lock-test", "status": "processing"},
        }

        with patch.object(
            EventRegistration.objects,
            "select_for_update",
            wraps=EventRegistration.objects.select_for_update,
        ) as mock_select_for_update:
            response = self.client.post(
                self.pay_url,
                {"method": "mobile_money", "phone_number": "+256700123456"},
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_select_for_update.assert_called_once()
        self.assertEqual(Payment.objects.count(), 1)
