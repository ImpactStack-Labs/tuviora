"""Event registration shared by the web API and USSD."""

from django.db import IntegrityError, OperationalError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import Event, EventRegistration, TicketType

HELD = (
    EventRegistration.Status.CONFIRMED,
    EventRegistration.Status.PAYMENT_PENDING,
)


class RegistrationError(Exception):
    def __init__(self, detail, http_status):
        super().__init__(detail)
        self.detail = detail
        self.http_status = http_status


def register_for_event(event_id, user, ticket_type_id=None):
    """Register user for a published event, respecting capacity."""
    try:
        with transaction.atomic():
            event = get_object_or_404(
                Event.objects.select_for_update(), pk=event_id,
            )

            if event.status != Event.Status.PUBLISHED:
                raise RegistrationError("Registration is not open.", 400)

            if event.date < timezone.localdate():
                raise RegistrationError("This event has already passed.", 400)

            active_ticket_types = TicketType.objects.filter(
                event=event, is_active=True,
            )
            ticket_type = None
            amount_due = None
            currency = ""

            if active_ticket_types.exists():
                if not ticket_type_id:
                    raise RegistrationError("Select a ticket type.", 400)

                try:
                    ticket_type = active_ticket_types.filter(
                        pk=ticket_type_id,
                    ).first()
                except (ValueError, TypeError):
                    ticket_type = None

                if ticket_type is None:
                    raise RegistrationError(
                        "Select a valid ticket type for this event.", 400,
                    )

                amount_due = ticket_type.price
                currency = ticket_type.currency

            registration_status = (
                EventRegistration.Status.CONFIRMED
                if amount_due is None or amount_due == 0
                else EventRegistration.Status.PAYMENT_PENDING
            )

            existing = EventRegistration.objects.filter(
                event=event, user=user,
            ).first()

            if existing and existing.status in HELD:
                raise RegistrationError("You are already registered.", 409)

            held_count = EventRegistration.objects.filter(
                event=event, status__in=HELD,
            ).count()

            if event.capacity is not None and held_count >= event.capacity:
                raise RegistrationError("This event is fully booked.", 409)

            if existing:
                existing.ticket_type = ticket_type
                existing.amount_due = amount_due
                existing.currency = currency
                existing.status = registration_status
                existing.save(
                    update_fields=[
                        "ticket_type",
                        "amount_due",
                        "currency",
                        "status",
                        "updated_at",
                    ]
                )
                return existing

            return EventRegistration.objects.create(
                event=event,
                user=user,
                ticket_type=ticket_type,
                amount_due=amount_due,
                currency=currency,
                status=registration_status,
            )

    except IntegrityError:
        raise RegistrationError("Registration conflict. Please retry.", 409)
    except OperationalError:
        raise RegistrationError("Registration is busy. Please retry.", 503)
