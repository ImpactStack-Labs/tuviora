# Ticket Types & Pricing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let organizers define priced ticket tiers for an event and let attendees pick one at registration, so a paid registration lands in a distinct `payment_pending` state instead of being silently confirmed for free.

**Architecture:** A new `TicketType` model (event-scoped, organizer-managed via a standard DRF `generics` CRUD pair) sits alongside the existing `Event` and `EventRegistration` models. `EventRegistration` gains a nullable `ticket_type` FK plus a snapshotted `amount_due`/`currency` (so later price edits never change what an already-registered attendee owes) and a new `payment_pending` status. The existing free-registration flow is untouched: an event with zero ticket types behaves exactly as it does today.

**Tech Stack:** Django 5/DRF (existing `apps.events`), React 19 + Vite (existing `CreateEvent.jsx` / `PublicEventDetail.jsx`), no new dependencies.

## Global Constraints

- No new backend or frontend dependencies — everything here is plain Django/DRF/React, matching the rest of `apps.events`.
- Money fields use `DecimalField(max_digits=10, decimal_places=2)` — never float — matching how the eventual payment provider (MarzPay) represents amounts.
- `currency` is restricted to the set MarzPay supports, so this model needs no rework in the follow-up payments plan: `UGX, KES, RWF, CDF, USD, ZMW, XAF, XOF, SLE`.
- Ticket-type management is organizer-only (same ownership check as `EventListCreateView`/`EventPublishView`: `Event.objects.filter(pk=event_id, organizer=request.user)`). Team roles (manager/member) are not extended here — that's a separate plan.
- An event with **no** `TicketType` rows is a free event. This is the flag — there is no separate `Event.is_paid` boolean to keep in sync.
- Frontend has no test runner configured (`frontend/package.json` has no vitest/jest) — do not add one for this plan. Frontend tasks end with a manual "run the dev server and check X" verification step instead of an automated test, matching how the rest of the frontend ships today.
- Backend tests use Django's own `APITestCase`/`SimpleTestCase` with `@patch`/`@override_settings` (see `apps/events/test_registration_api.py`, `apps/events/test_sms_service.py`) — no pytest.
- Run backend tests from `backend/`: `python manage.py test apps.events`.

---

### Task 1: `TicketType` model + `EventRegistration` pricing fields

**Files:**
- Modify: `backend/apps/events/models.py:486` (insert `TicketType` immediately before the `EventRegistration` class; modify `EventRegistration.Status` and add fields)
- Create: `backend/apps/events/migrations/0009_ticket_type_and_registration_pricing.py` (generated, not hand-written)
- Test: `backend/apps/events/test_ticket_types_api.py` (new file, model-level assertions only in this task — API assertions come in Task 2)

**Interfaces:**
- Produces: `TicketType(event, name, price, currency, is_active, created_at, updated_at)`, `TicketType.Currency` (`TextChoices`: UGX/KES/RWF/CDF/USD/ZMW/XAF/XOF/SLE), reverse accessor `event.ticket_types`.
- Produces: `EventRegistration.Status.PAYMENT_PENDING = "payment_pending"` (inserted before `CONFIRMED`), `EventRegistration.ticket_type` (nullable FK to `TicketType`, `related_name="registrations"`, `on_delete=SET_NULL`), `EventRegistration.amount_due` (nullable `DecimalField`), `EventRegistration.currency` (blank `CharField(max_length=3)`).

- [ ] **Step 1: Write the failing model test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python manage.py test apps.events.test_ticket_types_api -v 2`
Expected: FAIL — `ImportError: cannot import name 'TicketType'`

- [ ] **Step 3: Add the model**

In `backend/apps/events/models.py`, insert this class immediately before `class EventRegistration(models.Model):` (currently line 486):

```python
class TicketType(models.Model):
    class Currency(models.TextChoices):
        UGX = "UGX", "Ugandan Shilling"
        KES = "KES", "Kenyan Shilling"
        RWF = "RWF", "Rwandan Franc"
        CDF = "CDF", "Congolese Franc"
        USD = "USD", "US Dollar"
        ZMW = "ZMW", "Zambian Kwacha"
        XAF = "XAF", "Central African CFA Franc"
        XOF = "XOF", "West African CFA Franc"
        SLE = "SLE", "Sierra Leonean Leone"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="ticket_types",
    )

    name = models.CharField(max_length=100)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.UGX,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price", "id"]

    def __str__(self):
        return f"{self.name} - {self.event.name}"


```

Then update `EventRegistration` (same file, the class that follows):

```python
class EventRegistration(models.Model):
    """An attendee's registration for an event."""

    class Status(models.TextChoices):
        PAYMENT_PENDING = "payment_pending", "Payment Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations",
    )

    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registrations",
    )

    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )

    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"],
                name="unique_event_attendee_registration",
            ),
        ]
        ordering = ["-registered_at"]

    def __str__(self):
        return (
            f"{self.user} - {self.event} "
            f"({self.status})"
        )
```

(Only the additions — `ticket_type`, `amount_due`, `currency`, and the reordered `Status` — are new; everything else in `EventRegistration` is unchanged.)

- [ ] **Step 4: Generate and inspect the migration**

Run: `cd backend && python manage.py makemigrations events`
Expected: creates `apps/events/migrations/0009_...py` adding the `TicketType` model and altering `EventRegistration` (new fields + `AlterField` on `status` for the new choice). Open the generated file and confirm it only touches `TicketType` and `EventRegistration` — no unrelated model changes.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python manage.py migrate && python manage.py test apps.events.test_ticket_types_api -v 2`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/apps/events/models.py backend/apps/events/migrations/ backend/apps/events/test_ticket_types_api.py
git commit -m "feat(events): add TicketType model and registration pricing fields"
```

---

### Task 2: Organizer ticket-type CRUD API

**Files:**
- Create: `backend/apps/events/ticket_serializers.py`
- Create: `backend/apps/events/ticket_views.py`
- Modify: `backend/apps/events/urls.py:1-33` (imports) and `:35-138` (add two `path()` entries)
- Test: `backend/apps/events/test_ticket_types_api.py` (append to the file created in Task 1)

**Interfaces:**
- Consumes: `TicketType`, `Event` from `.models` (Task 1).
- Produces: `TicketTypeSerializer` (fields: `id, event, name, price, currency, is_active, created_at, updated_at`; `event` read-only), `EventTicketTypeListCreateView`, `EventTicketTypeDetailView`. URLs: `GET/POST /api/events/<event_id>/ticket-types/`, `GET/PATCH/DELETE /api/events/<event_id>/ticket-types/<pk>/`.

- [ ] **Step 1: Write the failing API tests**

Append to `backend/apps/events/test_ticket_types_api.py`. `User`, `Event`, `TicketType`, `timezone`, `timedelta` are already imported at the top of this file from Task 1 — only these two new imports are needed:

```python
from rest_framework import status
from rest_framework.test import APITestCase


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.events.test_ticket_types_api -v 2`
Expected: FAIL — `ImportError` / 404s for the not-yet-created endpoints.

- [ ] **Step 3: Write the serializer**

`backend/apps/events/ticket_serializers.py`:

```python
from rest_framework import serializers

from .models import TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TicketType
        fields = [
            "id",
            "event",
            "name",
            "price",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "event", "created_at", "updated_at"]
```

- [ ] **Step 4: Write the views**

`backend/apps/events/ticket_views.py`:

```python
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Event, TicketType
from .ticket_serializers import TicketTypeSerializer


class EventTicketTypeListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return get_object_or_404(
            Event,
            pk=self.kwargs["event_id"],
            organizer=self.request.user,
        )

    def get_queryset(self):
        return TicketType.objects.filter(event=self.get_event())

    def perform_create(self, serializer):
        serializer.save(event=self.get_event())


class EventTicketTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TicketTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TicketType.objects.filter(
            event_id=self.kwargs["event_id"],
            event__organizer=self.request.user,
        )
```

- [ ] **Step 5: Wire the URLs**

In `backend/apps/events/urls.py`, add to the imports near the top:

```python
from .ticket_views import (
    EventTicketTypeDetailView,
    EventTicketTypeListCreateView,
)
```

Add these two entries to `urlpatterns` (next to the other `<int:event_id>/...` routes, e.g. right after the `registrations/me/cancel/` entry):

```python
    path(
        "<int:event_id>/ticket-types/",
        EventTicketTypeListCreateView.as_view(),
        name="event-ticket-types",
    ),
    path(
        "<int:event_id>/ticket-types/<int:pk>/",
        EventTicketTypeDetailView.as_view(),
        name="event-ticket-type-detail",
    ),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.events.test_ticket_types_api -v 2`
Expected: PASS (6 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/apps/events/ticket_serializers.py backend/apps/events/ticket_views.py backend/apps/events/urls.py backend/apps/events/test_ticket_types_api.py
git commit -m "feat(events): add organizer ticket type CRUD API"
```

---

### Task 3: Registration endpoint branches on ticket type

**Files:**
- Modify: `backend/apps/events/registration_views.py:1-113` (`EventRegistrationView`)
- Modify: `backend/apps/events/registration_serializers.py` (`EventRegistrationSerializer`, `MyRegistrationsSerializer`)
- Test: `backend/apps/events/test_registration_api.py` (append; existing tests in this file must keep passing unmodified — they cover the free-event path)

**Interfaces:**
- Consumes: `TicketType`, `EventRegistration.Status.PAYMENT_PENDING` (Task 1).
- Produces: `POST /api/events/<id>/registrations/` now accepts optional JSON body `{"ticket_type_id": <int>}`; response gains `ticket_type`, `amount_due`, `currency`. Free events (no active ticket types) are unaffected — same 201 + `status: "confirmed"` as before.

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/events/test_registration_api.py` (inside `EventRegistrationAPITests`, or a new `TestCase` subclass in the same file — either is fine, match the existing style):

```python
class PriceRegistrationAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="priced_registration_organizer",
            password="TestPassword123!",
        )
        self.attendee = User.objects.create_user(
            username="priced_registration_attendee",
            password="TestPassword123!",
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Priced Registration Test",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        self.ticket = TicketType.objects.create(
            event=self.event,
            name="Standard",
            price="25000.00",
        )
        self.free_ticket = TicketType.objects.create(
            event=self.event,
            name="Complimentary",
            price="0.00",
        )
        self.registration_url = (
            f"/api/events/{self.event.id}/registrations/"
        )
        self.client.force_authenticate(user=self.attendee)

    def test_registering_for_priced_ticket_is_payment_pending(self):
        response = self.client.post(
            self.registration_url,
            {"ticket_type_id": self.ticket.id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "payment_pending")
        self.assertEqual(response.data["amount_due"], "25000.00")
        self.assertEqual(response.data["currency"], "UGX")

    def test_registering_for_zero_price_ticket_is_confirmed(self):
        response = self.client.post(
            self.registration_url,
            {"ticket_type_id": self.free_ticket.id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "confirmed")

    def test_ticket_type_is_required_when_event_has_ticket_types(self):
        response = self.client.post(self.registration_url)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_ticket_type_from_another_event_is_rejected(self):
        other_event = Event.objects.create(
            organizer=self.organizer,
            name="Other Event",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Entebbe",
            status=Event.Status.PUBLISHED,
        )
        other_ticket = TicketType.objects.create(
            event=other_event, name="Standard", price="10000.00"
        )
        response = self.client.post(
            self.registration_url,
            {"ticket_type_id": other_ticket.id},
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_payment_pending_counts_toward_capacity(self):
        self.event.capacity = 1
        self.event.save(update_fields=["capacity"])

        self.client.post(
            self.registration_url, {"ticket_type_id": self.ticket.id}
        )

        second_attendee = User.objects.create_user(
            username="priced_registration_attendee_2",
            password="TestPassword123!",
        )
        self.client.force_authenticate(user=second_attendee)

        response = self.client.post(
            self.registration_url, {"ticket_type_id": self.ticket.id}
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
```

Add `TicketType` to the existing `from .models import Event, EventRegistration` import line at the top of the file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.events.test_registration_api -v 2`
Expected: new tests FAIL (missing `ticket_type_id` handling); pre-existing tests in the file still PASS.

- [ ] **Step 3: Update the serializers**

In `backend/apps/events/registration_serializers.py`, add the three new fields to both serializers:

```python
class EventRegistrationSerializer(serializers.ModelSerializer):
    """Read-only representation of an attendee registration."""

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "event",
            "user",
            "ticket_type",
            "amount_due",
            "currency",
            "status",
            "registered_at",
            "updated_at",
        ]
        read_only_fields = fields



class MyRegistrationsSerializer(serializers.ModelSerializer):
    """An attendee's registration with public event information."""

    event = PublicEventSerializer(read_only=True)

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "event",
            "ticket_type",
            "amount_due",
            "currency",
            "status",
            "registered_at",
            "updated_at",
        ]
        read_only_fields = fields
```

- [ ] **Step 4: Update the registration view**

In `backend/apps/events/registration_views.py`, change the import line and the `post` method of `EventRegistrationView`:

```python
from .models import Event, EventRegistration, TicketType
```

Replace the body of `post` (everything inside the `with transaction.atomic():` block) with:

```python
        try:
            with transaction.atomic():
                event = get_object_or_404(
                    Event.objects.select_for_update(),
                    pk=event_id,
                )

                if event.status != Event.Status.PUBLISHED:
                    return Response(
                        {"detail": "Registration is not open."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if event.date < timezone.localdate():
                    return Response(
                        {"detail": "This event has already passed."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                active_ticket_types = TicketType.objects.filter(
                    event=event, is_active=True
                )
                ticket_type = None
                amount_due = None
                currency = ""

                if active_ticket_types.exists():
                    ticket_type_id = request.data.get("ticket_type_id")

                    if not ticket_type_id:
                        return Response(
                            {"detail": "Select a ticket type."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    ticket_type = active_ticket_types.filter(
                        pk=ticket_type_id
                    ).first()

                    if ticket_type is None:
                        return Response(
                            {
                                "detail": (
                                    "Select a valid ticket type "
                                    "for this event."
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    amount_due = ticket_type.price
                    currency = ticket_type.currency

                registration_status = (
                    EventRegistration.Status.CONFIRMED
                    if amount_due is None or amount_due == 0
                    else EventRegistration.Status.PAYMENT_PENDING
                )

                existing = EventRegistration.objects.filter(
                    event=event,
                    user=request.user,
                ).first()

                if existing and existing.status in (
                    EventRegistration.Status.CONFIRMED,
                    EventRegistration.Status.PAYMENT_PENDING,
                ):
                    return Response(
                        {"detail": "You are already registered."},
                        status=status.HTTP_409_CONFLICT,
                    )

                held_count = EventRegistration.objects.filter(
                    event=event,
                    status__in=[
                        EventRegistration.Status.CONFIRMED,
                        EventRegistration.Status.PAYMENT_PENDING,
                    ],
                ).count()

                if (
                    event.capacity is not None
                    and held_count >= event.capacity
                ):
                    return Response(
                        {"detail": "This event is fully booked."},
                        status=status.HTTP_409_CONFLICT,
                    )

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
                    registration = existing
                else:
                    registration = EventRegistration.objects.create(
                        event=event,
                        user=request.user,
                        ticket_type=ticket_type,
                        amount_due=amount_due,
                        currency=currency,
                        status=registration_status,
                    )
```

(The `except IntegrityError` / `except OperationalError` clauses and the final `return Response(...)` stay exactly as they are today.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.events.test_registration_api -v 2`
Expected: PASS, including every pre-existing test in the file (free-registration behavior is unchanged since events with no `TicketType` rows never enter the new branch).

- [ ] **Step 6: Commit**

```bash
git add backend/apps/events/registration_views.py backend/apps/events/registration_serializers.py backend/apps/events/test_registration_api.py
git commit -m "feat(events): branch registration status on ticket type pricing"
```

---

### Task 4: Expose ticket types on the public event API + frontend API client

**Files:**
- Modify: `backend/apps/events/public_serializers.py`
- Modify: `frontend/src/lib/events.js`
- Test: `backend/apps/events/test_public_events_api.py` (append)

**Interfaces:**
- Consumes: `TicketTypeSerializer` (Task 2).
- Produces: `PublicEventSerializer` output gains `"ticket_types": [...]` (only `is_active=True` rows). Frontend gains `getEventTicketTypes(eventId)`, `createTicketType(eventId, data)`; `registerForEvent(eventId, ticketTypeId)` gains an optional second argument.

- [ ] **Step 1: Write the failing test**

Append to `backend/apps/events/test_public_events_api.py` (check the top of that file for its existing `User`/`Event` setup pattern and match it; the new test is self-contained regardless):

```python
class PublicEventTicketTypesTests(APITestCase):
    def setUp(self):
        self.organizer = get_user_model().objects.create_user(
            username="public_ticket_organizer",
            password="TestPassword123!",
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Public Ticket Test",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        TicketType.objects.create(
            event=self.event, name="Standard", price="25000.00"
        )
        TicketType.objects.create(
            event=self.event,
            name="Retired",
            price="10000.00",
            is_active=False,
        )

    def test_public_event_only_lists_active_ticket_types(self):
        response = self.client.get(f"/api/events/public/{self.event.id}/")
        names = [t["name"] for t in response.data["ticket_types"]]
        self.assertEqual(names, ["Standard"])
```

Add the necessary imports at the top of the file if not already present: `from django.contrib.auth import get_user_model`, `from datetime import timedelta`, `from django.utils import timezone`, `from .models import Event, TicketType`, `from rest_framework.test import APITestCase` — check what's already imported first and only add what's missing.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python manage.py test apps.events.test_public_events_api -v 2`
Expected: FAIL — `KeyError: 'ticket_types'`

- [ ] **Step 3: Update the public serializer**

Replace `backend/apps/events/public_serializers.py` in full:

```python
from rest_framework import serializers

from .models import Event


class PublicEventSerializer(serializers.ModelSerializer):
    """Public information available before registration."""

    ticket_types = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "category",
            "description",
            "date",
            "timezone_name",
            "start_time",
            "end_time",
            "event_format",
            "venue",
            "landmark",
            "capacity",
            "ticket_types",
        ]
        read_only_fields = [
            "id",
            "name",
            "category",
            "description",
            "date",
            "timezone_name",
            "start_time",
            "end_time",
            "event_format",
            "venue",
            "landmark",
            "capacity",
        ]

    def get_ticket_types(self, obj):
        from .ticket_serializers import TicketTypeSerializer

        active = obj.ticket_types.filter(is_active=True)
        return TicketTypeSerializer(active, many=True).data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python manage.py test apps.events.test_public_events_api -v 2`
Expected: PASS

- [ ] **Step 5: Add the frontend API client functions**

In `frontend/src/lib/events.js`, add after `getMyRegistrations`:

```js
export function getEventTicketTypes(eventId) {
  return apiRequest(`/api/events/${eventId}/ticket-types/`)
}

export function createTicketType(eventId, ticketType) {
  return apiRequest(`/api/events/${eventId}/ticket-types/`, {
    method: 'POST',
    body: JSON.stringify(ticketType),
  })
}
```

Replace the existing `registerForEvent`:

```js
export function registerForEvent(eventId, ticketTypeId) {
  return apiRequest(`/api/events/${eventId}/registrations/`, {
    method: 'POST',
    body: ticketTypeId
      ? JSON.stringify({ ticket_type_id: ticketTypeId })
      : undefined,
  })
}
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/events/public_serializers.py backend/apps/events/test_public_events_api.py frontend/src/lib/events.js
git commit -m "feat(events): expose active ticket types on the public event API"
```

---

### Task 5: Organizer UI — define ticket types when creating an event

**Files:**
- Modify: `frontend/src/pages/CreateEvent.jsx`

**Interfaces:**
- Consumes: `createEvent` (existing), `createTicketType(eventId, {name, price, currency})` (Task 4).

- [ ] **Step 1: Add paid-event state**

In `frontend/src/pages/CreateEvent.jsx`, add to `initialForm` (after `capacity: '',`):

```js
  isPaid: false,
  ticketTypes: [{ key: 0, name: '', price: '', currency: 'UGX' }],
```

Import `createTicketType` alongside the existing import:

```js
import { createEvent, createTicketType, formatApiError } from '../lib/events'
```

Add these two helpers next to `updateLocation` (same component, before `handleSubmit`):

```js
  function updateTicketType(key, field, value) {
    setForm((previous) => ({
      ...previous,
      ticketTypes: previous.ticketTypes.map((ticket) =>
        ticket.key === key ? { ...ticket, [field]: value } : ticket,
      ),
    }))
  }

  function addTicketType() {
    setForm((previous) => ({
      ...previous,
      ticketTypes: [
        ...previous.ticketTypes,
        { key: Date.now(), name: '', price: '', currency: 'UGX' },
      ],
    }))
  }

  function removeTicketType(key) {
    setForm((previous) => ({
      ...previous,
      ticketTypes: previous.ticketTypes.filter((t) => t.key !== key),
    }))
  }
```

- [ ] **Step 2: Create ticket types after the event is created**

In `handleSubmit`, replace:

```js
    try {
      await createEvent(payload)
      navigate('/operations/events', {
        state: { message: 'Event created successfully as a draft.' },
      })
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSaving(false)
    }
```

with:

```js
    try {
      const created = await createEvent(payload)

      if (form.isPaid) {
        const validTickets = form.ticketTypes.filter(
          (t) => t.name.trim() && Number(t.price) > 0,
        )

        for (const ticket of validTickets) {
          // ponytail: sequential, not Promise.all — keeps ticket type
          // order predictable and errors attributable to one row.
          // Revisit if organizers routinely add >10 tiers.
          await createTicketType(created.id, {
            name: ticket.name.trim(),
            price: Number(ticket.price),
            currency: ticket.currency,
          })
        }
      }

      navigate('/operations/events', {
        state: { message: 'Event created successfully as a draft.' },
      })
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSaving(false)
    }
```

- [ ] **Step 3: Add the "Tickets & Pricing" section**

Insert this new `<section>` in the JSX, between the closing `</section>` of "Date and location" and the `<div className="flex items-start gap-3 rounded-xl border border-[#E8E1C7] ...">` info banner:

```jsx
        <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6 sm:p-8">
          <h2 className="text-xl font-bold">Tickets &amp; pricing</h2>
          <p className="mt-2 text-sm text-[#647064]">
            Leave this off for a free event. Turn it on to charge
            attendees and offer more than one ticket tier.
          </p>

          <label className="mt-5 flex items-center gap-3">
            <input
              type="checkbox"
              checked={form.isPaid}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  isPaid: event.target.checked,
                }))
              }
            />
            <span className="font-semibold">This is a paid event</span>
          </label>

          {form.isPaid && (
            <div className="mt-6 space-y-4">
              {form.ticketTypes.map((ticket) => (
                <div
                  key={ticket.key}
                  className="grid gap-3 rounded-xl border border-[#DCE5D8] p-4 sm:grid-cols-[2fr_1fr_1fr_auto]"
                >
                  <input
                    value={ticket.name}
                    onChange={(event) =>
                      updateTicketType(ticket.key, 'name', event.target.value)
                    }
                    placeholder="e.g. Standard"
                    className={fieldClass}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={ticket.price}
                    onChange={(event) =>
                      updateTicketType(ticket.key, 'price', event.target.value)
                    }
                    placeholder="Price"
                    className={fieldClass}
                  />
                  <select
                    value={ticket.currency}
                    onChange={(event) =>
                      updateTicketType(
                        ticket.key,
                        'currency',
                        event.target.value,
                      )
                    }
                    className={fieldClass}
                  >
                    <option value="UGX">UGX</option>
                    <option value="KES">KES</option>
                    <option value="RWF">RWF</option>
                    <option value="CDF">CDF</option>
                    <option value="USD">USD</option>
                    <option value="ZMW">ZMW</option>
                    <option value="XAF">XAF</option>
                    <option value="XOF">XOF</option>
                    <option value="SLE">SLE</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => removeTicketType(ticket.key)}
                    disabled={form.ticketTypes.length === 1}
                    className="rounded-xl border border-[#DCE5D8] px-4 py-2 text-sm font-semibold text-[#1A3F22] disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>
              ))}

              <button
                type="button"
                onClick={addTicketType}
                className="rounded-xl border border-[#58761B] px-4 py-2 text-sm font-semibold text-[#58761B]"
              >
                Add another ticket type
              </button>
            </div>
          )}
        </section>

```

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev`
1. Open the "Create an event" page, fill in required fields, toggle "This is a paid event", add two ticket rows (e.g. "Early Bird" 15000 UGX, "Standard" 25000 UGX), submit.
2. Confirm the redirect to My Events happens and no error banner appears.
3. In a new browser tab, call `GET /api/events/public/<new-event-id>/` (once published) or check the Django admin / `python manage.py shell` — confirm two `TicketType` rows exist for that event with the entered names/prices.
4. Create a second event without checking "paid" — confirm zero `TicketType` rows are created for it (existing free-event behavior).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CreateEvent.jsx
git commit -m "feat(frontend): let organizers define ticket types when creating an event"
```

---

### Task 6: Attendee UI — pick a ticket type at registration

**Files:**
- Modify: `frontend/src/pages/PublicEventDetail.jsx`

**Interfaces:**
- Consumes: `event.ticket_types` (Task 4's public serializer field), `registerForEvent(eventId, ticketTypeId)` (Task 4).

- [ ] **Step 1: Add ticket-type selection state**

In `frontend/src/pages/PublicEventDetail.jsx`, add a new state hook next to the existing ones (after `const [registrationError, setRegistrationError] = useState('')`):

```js
  const [selectedTicketTypeId, setSelectedTicketTypeId] = useState(null)
```

- [ ] **Step 2: Default-select the first ticket type once the event loads**

In the `loadEvent` effect, right after `setEvent(selected)`, add:

```js
        if (selected.ticket_types?.length) {
          setSelectedTicketTypeId(selected.ticket_types[0].id)
        }
```

- [ ] **Step 3: Pass the selection through on register**

Change `handleRegister`'s call from `registerForEvent(eventId)` to:

```js
      const result = await registerForEvent(eventId, selectedTicketTypeId)
```

- [ ] **Step 4: Render the ticket picker and a payment-pending state**

In the JSX, inside the `user ? (...)` branch, right before the existing `{registration?.status === 'confirmed' ? (` block, insert:

```jsx
                    {event.ticket_types?.length > 0 &&
                      !registration && (
                        <fieldset className="mt-6 space-y-3">
                          <legend className="font-semibold">
                            Choose a ticket
                          </legend>
                          {event.ticket_types.map((ticket) => (
                            <label
                              key={ticket.id}
                              className="flex items-center justify-between rounded-xl border border-[#DCE5D8] p-4"
                            >
                              <span className="flex items-center gap-3">
                                <input
                                  type="radio"
                                  name="ticket_type"
                                  checked={selectedTicketTypeId === ticket.id}
                                  onChange={() =>
                                    setSelectedTicketTypeId(ticket.id)
                                  }
                                />
                                {ticket.name}
                              </span>
                              <span className="font-semibold">
                                {Number(ticket.price) > 0
                                  ? `${ticket.price} ${ticket.currency}`
                                  : 'Free'}
                              </span>
                            </label>
                          ))}
                        </fieldset>
                      )}

```

And add a `payment_pending` branch as a sibling of the existing `confirmed`/else branches — change:

```jsx
                    {registration?.status === 'confirmed' ? (
```

to:

```jsx
                    {registration?.status === 'payment_pending' ? (
                      <div
                        role="status"
                        className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
                      >
                        Your spot is reserved. Payment collection is
                        coming soon — you'll be notified how to pay.
                      </div>
                    ) : registration?.status === 'confirmed' ? (
```

(Leave the rest of that ternary chain — the `cancelled` message and the register/cancel buttons — exactly as it is.)

- [ ] **Step 5: Manual verification**

Run: `cd frontend && npm run dev`
1. Open a published free event's public page (no ticket types) as a signed-in attendee — confirm the register flow is unchanged (no ticket picker shown, register still goes straight to "confirmed").
2. Open a published paid event created in Task 5 — confirm the ticket picker renders, the first ticket is pre-selected, and registering shows the new amber "spot is reserved" banner with `status: payment_pending` (check via `GET /api/events/<id>/registrations/me/`).
3. Confirm capacity: set the event's capacity to 1 in Django admin, register once (payment_pending), then try registering as a second user — confirm "This event is fully booked."

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PublicEventDetail.jsx
git commit -m "feat(frontend): let attendees choose a ticket type at registration"
```

---

## Known limitation (intentional, not a bug)

Paid registrations stop at `payment_pending` with no way to reach `confirmed` — there is no payment collection yet. That's the seam for the next plan (MarzPay payment collection), which adds a `Payment` model, initiates a MarzPay collection on registration, and confirms the registration from MarzPay's webhook. If a `createTicketType` call in Task 5 fails partway through the loop, the event is already created as a draft with only the ticket types that succeeded — there is no ticket-type edit page yet to fix this after the fact (`MyEvents.jsx` doesn't manage ticket types). Both are acceptable for this increment; flag either if it needs to move up in priority.
