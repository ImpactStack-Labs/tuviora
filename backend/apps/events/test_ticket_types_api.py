"""Tests for ticket types and priced event registration."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from .models import Event, TicketType
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class TicketTypeModelTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="ticket_organizer",
            password="TestPassword123!",
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Ticketing Test",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )

    def test_ticket_type_defaults_to_ugx(self):
        ticket = TicketType.objects.create(
            event=self.event,
            name="Standard",
            price=Decimal("25000.00"),
        )
        self.assertEqual(ticket.currency, TicketType.Currency.UGX)
        self.assertTrue(ticket.is_active)

    def test_ticket_types_ordered_by_price(self):
        TicketType.objects.create(
            event=self.event, name="VIP", price=Decimal("100000.00")
        )
        TicketType.objects.create(
            event=self.event, name="Early Bird", price=Decimal("15000.00")
        )
        prices = list(
            self.event.ticket_types.values_list("price", flat=True)
        )
        self.assertEqual(
            prices, [Decimal("15000.00"), Decimal("100000.00")]
        )


class TicketTypeAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="ticket_api_organizer",
            password="TestPassword123!",
        )
        self.other_organizer = User.objects.create_user(
            username="ticket_api_other",
            password="TestPassword123!",
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Ticket API Test",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        self.list_url = f"/api/events/{self.event.id}/ticket-types/"
        self.client.force_authenticate(user=self.organizer)

    def test_organizer_can_create_ticket_type(self):
        response = self.client.post(
            self.list_url,
            {"name": "VIP", "price": "150000.00", "currency": "UGX"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["event"], self.event.id)
        self.assertEqual(TicketType.objects.count(), 1)

    def test_negative_price_is_rejected(self):
        response = self.client.post(
            self.list_url,
            {"name": "Broken", "price": "-10.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_organizer_cannot_manage_ticket_types(self):
        self.client.force_authenticate(user=self.other_organizer)
        response = self.client.post(
            self.list_url,
            {"name": "VIP", "price": "150000.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organizer_can_update_and_deactivate_ticket_type(self):
        ticket = TicketType.objects.create(
            event=self.event, name="Standard", price="25000.00"
        )
        detail_url = f"{self.list_url}{ticket.id}/"

        response = self.client.patch(detail_url, {"is_active": False})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertFalse(ticket.is_active)
