from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    BudgetItem,
    Event,
    EventMembership,
    EventRegistration,
    Feedback,
    Payment,
    RegistrationTicket,
    TicketType,
)

User = get_user_model()


class SummaryAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="org")
        self.manager = User.objects.create_user(username="mgr")
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Summary Event",
            category=Event.Category.CONCERT,
            date=timezone.localdate(),
            start_time="18:00",
            end_time="23:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        EventMembership.objects.create(
            event=self.event, user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        self.url = f"/api/events/{self.event.id}/summary/"

    def register(self, username, reg_status, ticket=None, amount=None):
        return EventRegistration.objects.create(
            event=self.event,
            user=User.objects.create_user(username=username),
            status=reg_status,
            ticket_type=ticket,
            amount_due=amount,
            currency="UGX" if amount else "",
        )

    def test_empty_event(self):
        self.client.force_authenticate(user=self.manager)
        data = self.client.get(self.url).data

        self.assertEqual(data["currency"], "UGX")
        self.assertEqual(data["attendance"]["rate"], 0.0)
        self.assertEqual(data["payments"]["collected"], "0.00")
        self.assertEqual(data["budget"]["net"], "0.00")
        self.assertIsNone(data["feedback"]["average_rating"])

    def test_aggregates(self):
        vip = TicketType.objects.create(
            event=self.event, name="VIP", price=Decimal("50000"), currency="UGX",
        )
        paid = self.register("a", EventRegistration.Status.CONFIRMED, vip, Decimal("50000"))
        free = self.register("b", EventRegistration.Status.CONFIRMED)
        self.register("c", EventRegistration.Status.PAYMENT_PENDING, vip, Decimal("50000"))
        self.register("d", EventRegistration.Status.CANCELLED)

        Payment.objects.create(
            registration=paid, reference="r1", method="mobile_money",
            amount=Decimal("50000"), currency="UGX", status="completed",
        )
        Payment.objects.create(
            registration=paid, reference="r2", method="mobile_money",
            amount=Decimal("50000"), currency="UGX", status="failed",
        )
        RegistrationTicket.objects.create(registration=paid, checked_in_at=timezone.now())
        RegistrationTicket.objects.create(registration=free)
        BudgetItem.objects.create(
            event=self.event, category="venue", description="Hall",
            planned_amount=Decimal("30000"), actual_amount=Decimal("35000"), paid=True,
        )
        BudgetItem.objects.create(
            event=self.event, category="catering", description="Food",
            planned_amount=Decimal("10000"),
        )
        Feedback.objects.create(event=self.event, attendee=paid.user, rating=5)
        Feedback.objects.create(event=self.event, attendee=free.user, rating=3)

        self.client.force_authenticate(user=self.organizer)
        data = self.client.get(self.url).data

        regs = data["registrations"]
        self.assertEqual(
            (regs["confirmed"], regs["payment_pending"], regs["cancelled"]), (2, 1, 1),
        )
        self.assertEqual(regs["by_ticket_type"], [{"name": "VIP", "count": 2}])
        self.assertEqual(sum(d["count"] for d in regs["by_day"]), 4)
        self.assertEqual(
            data["attendance"], {"checked_in": 1, "confirmed": 2, "rate": 0.5},
        )
        self.assertEqual(
            data["payments"],
            {"collected": "50000.00", "pending": "50000.00", "failed_count": 1},
        )
        self.assertEqual(
            data["budget"],
            {"planned": "40000.00", "actual": "35000.00",
             "unpaid": "10000.00", "net": "15000.00"},
        )
        self.assertEqual(data["feedback"], {"average_rating": 4.0, "count": 2})

    def test_payments_list_is_organizer_only(self):
        paid = self.register("a", EventRegistration.Status.CONFIRMED, amount=Decimal("1000"))
        Payment.objects.create(
            registration=paid, reference="r1", method="card",
            amount=Decimal("1000"), currency="UGX", status="completed",
        )
        url = f"/api/events/{self.event.id}/payments/"

        self.client.force_authenticate(user=self.manager)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["attendee"], "a")
        self.assertEqual(response.data[0]["status"], "completed")
