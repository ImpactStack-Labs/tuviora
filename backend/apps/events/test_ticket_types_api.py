"""Tests for ticket types and priced event registration."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from .models import Event, TicketType

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
