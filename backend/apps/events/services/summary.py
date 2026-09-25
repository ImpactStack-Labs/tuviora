"""Read-only aggregates for the Payments, Analytics and Budget pages."""

from decimal import Decimal

from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import Coalesce, TruncDate

from ..models import (
    EventRegistration,
    Payment,
    RegistrationTicket,
    TicketType,
)

ZERO = Decimal("0.00")


def money(value):
    return f"{(value or ZERO):.2f}"


def event_currency(event):
    ticket = (
        TicketType.objects.filter(event=event, is_active=True)
        .order_by("pk")
        .first()
    )
    return ticket.currency if ticket else "UGX"


def event_summary(event):
    registrations = EventRegistration.objects.filter(event=event)
    by_status = dict(
        registrations.values_list("status").annotate(n=Count("id"))
    )
    confirmed = by_status.get(EventRegistration.Status.CONFIRMED, 0)

    checked_in = RegistrationTicket.objects.filter(
        registration__event=event,
        registration__status=EventRegistration.Status.CONFIRMED,
        checked_in_at__isnull=False,
    ).count()

    payments = Payment.objects.filter(registration__event=event)
    collected = payments.filter(
        status=Payment.Status.COMPLETED,
    ).aggregate(total=Sum("amount"))["total"]
    pending = registrations.filter(
        status=EventRegistration.Status.PAYMENT_PENDING,
    ).aggregate(total=Sum("amount_due"))["total"]

    items = event.budget_items.all()
    planned = items.aggregate(total=Sum("planned_amount"))["total"]
    actual = items.aggregate(total=Sum("actual_amount"))["total"]
    unpaid = items.filter(paid=False).aggregate(
        total=Sum(Coalesce("actual_amount", "planned_amount"))
    )["total"]

    feedback = event.feedback.aggregate(
        average=Avg("rating"),
        count=Count("id"),
    )

    return {
        "currency": event_currency(event),
        "registrations": {
            "confirmed": confirmed,
            "payment_pending": by_status.get(
                EventRegistration.Status.PAYMENT_PENDING, 0
            ),
            "cancelled": by_status.get(EventRegistration.Status.CANCELLED, 0),
            "by_day": [
                {"date": row["day"].isoformat(), "count": row["count"]}
                for row in registrations
                .annotate(day=TruncDate("registered_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            ],
            "by_ticket_type": [
                {"name": row["name"], "count": row["count"]}
                for row in registrations
                .filter(ticket_type__isnull=False)
                .values(name=F("ticket_type__name"))
                .annotate(count=Count("id"))
                .order_by("name")
            ],
        },
        "attendance": {
            "checked_in": checked_in,
            "confirmed": confirmed,
            "rate": round(checked_in / confirmed, 3) if confirmed else 0.0,
        },
        "payments": {
            "collected": money(collected),
            "pending": money(pending),
            "failed_count": payments.filter(
                status=Payment.Status.FAILED,
            ).count(),
        },
        "budget": {
            "planned": money(planned),
            "actual": money(actual),
            "unpaid": money(unpaid),
            "net": money((collected or ZERO) - (actual or ZERO)),
        },
        "feedback": {
            "average_rating": (
                round(feedback["average"], 1)
                if feedback["average"] is not None
                else None
            ),
            "count": feedback["count"],
        },
    }
