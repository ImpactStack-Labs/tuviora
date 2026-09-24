# MarzPay Payment Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an attendee with a `payment_pending` registration actually pay (Mobile Money push or card redirect) through MarzPay, and have MarzPay's webhook automatically confirm the registration and record the transaction.

**Architecture:** A new `Payment` model records every collection attempt against an `EventRegistration` (one registration can have several `Payment` rows if an attempt fails and the attendee retries). A thin `marzpay_service` module wraps MarzPay's `/collect-money` and `/transactions/{id}` REST endpoints and its HMAC-SHA256 webhook signature scheme — no SDK, just `requests` (already a dependency). One endpoint lets the attendee start a payment; one public webhook endpoint lets MarzPay confirm it. Registration confirmation and the payment-confirmation SMS both happen from the webhook, not from the initiate call, since MarzPay never guarantees synchronous completion (mobile money is an async STK-style push).

**Tech Stack:** Django/DRF (existing `apps.events`), `requests` (already in `backend/requirements.txt`), no new backend dependencies. React (existing `PublicEventDetail.jsx`).

**Depends on:** `docs/superpowers/plans/2026-09-24-ticket-types-pricing.md` — this plan assumes `EventRegistration.status == "payment_pending"`, `.amount_due`, and `.currency` already exist (Task 1 of that plan). Execute that plan first.

## Global Constraints

- No new dependencies. The MarzPay integration is plain `requests` calls, matching how `sms_service.py` wraps `africastalking` — a small service module, not an SDK.
- MarzPay auth is **HTTP Basic**, not a bearer token: `Authorization: Basic base64(api_key:api_secret)`, sent on every request.
- MarzPay's `/collect-money` expects `multipart/form-data` (its own docs show `curl --form ...`), not JSON — use `requests`' `files={key: (None, value)}` trick to send plain fields as multipart, not `json=` or `data=`.
- Webhook signature: header `X-MarzPay-Signature: t={timestamp},v1={hex}` where `hex = HMAC-SHA256(secret, f"{timestamp}.{raw_body}")`. Verify with `hmac.compare_digest`, never `==`. Reject (400) anything that doesn't verify — never process an unverified payload.
- MarzPay only calls back on **final** statuses (`completed`/`failed`/`cancelled`) — never for `pending`/`processing`. Always return HTTP 200 once the payload is authenticated and handled, so MarzPay doesn't retry indefinitely.
- DRF's `APIView.as_view()` already disables Django's CSRF middleware for that view — do not add `@csrf_exempt`, it's redundant and the codebase has no other example of it.
- Single-market MVP: MarzPay's `country` field is hardcoded to `MARZPAY_DEFAULT_COUNTRY` (env-configurable, defaults `"UG"`) rather than inferred per-attendee. Mark this with a `ponytail:` comment — expanding beyond Uganda means resolving `country` from the attendee's phone prefix or an explicit organizer-set field, not guessed from currency (MarzPay's `XAF`/`XOF` currencies span several countries each, so currency alone is ambiguous).
- No refund handling. The brief explicitly places "Automated refunds" outside the MVP (§15) — do not add a `refunded` status or a refund endpoint.
- Payment confirmation SMS reuses the existing consent-aware `send_event_sms([user_id], message)` helper (`apps/events/services/event_sms_notifications.py`) — do not write a new SMS-sending path; that helper already checks `SMSPreference.sms_enabled` and swallows per-recipient failures.
- Backend tests: Django `APITestCase`/`SimpleTestCase` with `@patch`/`@override_settings`, run via `cd backend && python manage.py test apps.events`. No pytest.
- Frontend has no test runner — frontend tasks end with a manual verification step, not an automated test.

---

### Task 1: `Payment` model

**Files:**
- Modify: `backend/apps/events/models.py` (append after `EventRegistration`, which ends the file)
- Create: `backend/apps/events/migrations/0010_payment.py` (generated)
- Test: `backend/apps/events/test_payments_api.py` (new file, model-level only in this task)

**Interfaces:**
- Produces: `Payment(registration, reference, provider_transaction_id, method, phone_number, amount, currency, status, redirect_url, raw_response, created_at, updated_at)`, `Payment.Method` (`mobile_money`/`card`), `Payment.Status` (`pending`/`processing`/`completed`/`failed`/`cancelled`), reverse accessor `registration.payments`.

- [ ] **Step 1: Write the failing model test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python manage.py test apps.events.test_payments_api -v 2`
Expected: FAIL — `ImportError: cannot import name 'Payment'`

- [ ] **Step 3: Add the model**

Append to the end of `backend/apps/events/models.py`:

```python


class Payment(models.Model):
    class Method(models.TextChoices):
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        CARD = "card", "Card"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    registration = models.ForeignKey(
        EventRegistration,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    reference = models.CharField(max_length=64, unique=True)

    provider_transaction_id = models.CharField(
        max_length=64,
        blank=True,
    )

    method = models.CharField(
        max_length=20,
        choices=Method.choices,
    )

    phone_number = models.CharField(max_length=20, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(max_length=3)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    redirect_url = models.URLField(blank=True)

    raw_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} ({self.status})"
```

- [ ] **Step 4: Generate the migration**

Run: `cd backend && python manage.py makemigrations events`
Expected: creates `apps/events/migrations/0010_payment.py` adding only the `Payment` model.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python manage.py migrate && python manage.py test apps.events.test_payments_api -v 2`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/apps/events/models.py backend/apps/events/migrations/ backend/apps/events/test_payments_api.py
git commit -m "feat(events): add Payment model for MarzPay collections"
```

---

### Task 2: `marzpay_service` — API client and webhook verification

**Files:**
- Create: `backend/apps/events/services/marzpay_service.py`
- Modify: `backend/config/settings.py` (insert after the `AFRICASTALKING_SENDER_ID` line)
- Modify: `.env.example` (append a new section)
- Test: `backend/apps/events/test_marzpay_service.py` (new file)

**Interfaces:**
- Produces: `MarzPayError` (Exception), `initiate_collection(*, amount, currency, reference, method="mobile_money", phone_number=None, description="", callback_url=None, country=None) -> dict` (returns the provider's `data` object), `get_transaction(transaction_id) -> dict`, `verify_webhook_signature(raw_body, timestamp, signature_header, secret) -> bool`.
- Consumes settings: `MARZPAY_BASE_URL`, `MARZPAY_API_KEY`, `MARZPAY_API_SECRET`, `MARZPAY_DEFAULT_COUNTRY`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the MarzPay payment service."""

import hashlib
import hmac
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from apps.events.services.marzpay_service import (
    MarzPayError,
    get_transaction,
    initiate_collection,
    verify_webhook_signature,
)


@override_settings(
    MARZPAY_BASE_URL="https://wallet.wearemarz.com/api/v1",
    MARZPAY_API_KEY="test-key",
    MARZPAY_API_SECRET="test-secret",
    MARZPAY_DEFAULT_COUNTRY="UG",
)
class MarzPayCollectionTests(SimpleTestCase):
    @patch("apps.events.services.marzpay_service.requests")
    def test_initiate_mobile_money_collection(self, mock_requests):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "status": "success",
            "message": "Collection initiated successfully.",
            "data": {
                "transaction": {
                    "uuid": "4e7fb3fa-c13a-4b05-8acd-cf60ff68cb94",
                    "reference": "ref-123",
                    "status": "processing",
                },
                "collection": {"provider": "mtn"},
            },
        }
        mock_requests.post.return_value = mock_response

        result = initiate_collection(
            amount="1000",
            currency="UGX",
            reference="ref-123",
            method="mobile_money",
            phone_number="+256700000000",
        )

        self.assertEqual(
            result["transaction"]["status"], "processing"
        )

        _, kwargs = mock_requests.post.call_args
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            "Basic dGVzdC1rZXk6dGVzdC1zZWNyZXQ=",
        )
        sent_fields = {k: v[1] for k, v in kwargs["files"].items()}
        self.assertEqual(sent_fields["phone_number"], "+256700000000")
        self.assertEqual(sent_fields["country"], "UG")

    @patch("apps.events.services.marzpay_service.requests")
    def test_mobile_money_requires_phone_number(self, mock_requests):
        with self.assertRaises(MarzPayError):
            initiate_collection(
                amount="1000",
                currency="UGX",
                reference="ref-124",
                method="mobile_money",
            )
        mock_requests.post.assert_not_called()

    @patch("apps.events.services.marzpay_service.requests")
    def test_provider_error_raises_marzpay_error(self, mock_requests):
        mock_response = Mock(status_code=400)
        mock_response.json.return_value = {
            "status": "error",
            "message": "Insufficient collection limit.",
        }
        mock_requests.post.return_value = mock_response

        with self.assertRaises(MarzPayError):
            initiate_collection(
                amount="1000",
                currency="UGX",
                reference="ref-125",
                method="mobile_money",
                phone_number="+256700000000",
            )

    @patch("apps.events.services.marzpay_service.requests")
    def test_network_failure_raises_marzpay_error(self, mock_requests):
        import requests as real_requests

        mock_requests.RequestException = real_requests.RequestException
        mock_requests.post.side_effect = real_requests.RequestException(
            "boom"
        )

        with self.assertRaises(MarzPayError):
            initiate_collection(
                amount="1000",
                currency="UGX",
                reference="ref-126",
                method="mobile_money",
                phone_number="+256700000000",
            )

    @patch("apps.events.services.marzpay_service.requests")
    def test_get_transaction(self, mock_requests):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"transaction": {"status": "completed"}}
        mock_requests.get.return_value = mock_response

        result = get_transaction("ref-123")

        self.assertEqual(result["transaction"]["status"], "completed")
        mock_requests.get.assert_called_once()


class MarzPayWebhookSignatureTests(SimpleTestCase):
    def test_valid_signature_is_accepted(self):
        secret = "webhook-secret"
        timestamp = "1700000000"
        body = b'{"event_type":"collection.completed"}'
        digest = hmac.new(
            secret.encode(),
            f"{timestamp}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()

        self.assertTrue(
            verify_webhook_signature(
                body, timestamp, f"t={timestamp},v1={digest}", secret
            )
        )

    def test_tampered_signature_is_rejected(self):
        self.assertFalse(
            verify_webhook_signature(
                b'{"event_type":"collection.completed"}',
                "1700000000",
                "t=1700000000,v1=deadbeef",
                "webhook-secret",
            )
        )

    def test_missing_secret_is_rejected(self):
        self.assertFalse(
            verify_webhook_signature(
                b"{}", "1700000000", "t=1700000000,v1=abc", ""
            )
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.events.test_marzpay_service -v 2`
Expected: FAIL — `ImportError: No module named 'apps.events.services.marzpay_service'`

- [ ] **Step 3: Add the settings**

In `backend/config/settings.py`, insert after the existing block:

```python
AFRICASTALKING_SENDER_ID = os.getenv(
    "AFRICASTALKING_SENDER_ID", ""
)
```

add:

```python

# MarzPay payment collection (https://wallet.wearemarz.com)
MARZPAY_BASE_URL = os.getenv(
    "MARZPAY_BASE_URL", "https://wallet.wearemarz.com/api/v1"
).strip()
MARZPAY_API_KEY = os.getenv("MARZPAY_API_KEY", "").strip()
MARZPAY_API_SECRET = os.getenv("MARZPAY_API_SECRET", "").strip()
MARZPAY_WEBHOOK_SECRET = os.getenv(
    "MARZPAY_WEBHOOK_SECRET", ""
).strip()
MARZPAY_CALLBACK_URL = os.getenv("MARZPAY_CALLBACK_URL", "").strip()
MARZPAY_DEFAULT_COUNTRY = os.getenv(
    "MARZPAY_DEFAULT_COUNTRY", "UG"
).strip()
```

- [ ] **Step 4: Document the new env vars**

Append to `.env.example`:

```
# MarzPay (wallet.wearemarz.com) payment collection
MARZPAY_BASE_URL=https://wallet.wearemarz.com/api/v1
MARZPAY_API_KEY=
MARZPAY_API_SECRET=
MARZPAY_WEBHOOK_SECRET=
MARZPAY_CALLBACK_URL=
MARZPAY_DEFAULT_COUNTRY=UG
```

- [ ] **Step 5: Write the service**

`backend/apps/events/services/marzpay_service.py`:

```python
"""MarzPay collections integration (https://wallet.wearemarz.com)."""

import base64
import hashlib
import hmac
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MarzPayError(Exception):
    """Raised when a MarzPay API call cannot be completed."""


def _base_url():
    return getattr(
        settings,
        "MARZPAY_BASE_URL",
        "https://wallet.wearemarz.com/api/v1",
    )


def _auth_header():
    api_key = getattr(settings, "MARZPAY_API_KEY", "")
    api_secret = getattr(settings, "MARZPAY_API_SECRET", "")

    if not api_key or not api_secret:
        raise MarzPayError(
            "MarzPay API credentials are not configured."
        )

    credentials = base64.b64encode(
        f"{api_key}:{api_secret}".encode()
    ).decode()

    return {"Authorization": f"Basic {credentials}"}


def initiate_collection(
    *,
    amount,
    currency,
    reference,
    method="mobile_money",
    phone_number=None,
    description="",
    callback_url=None,
    country=None,
):
    """Start a MarzPay collection. Returns the provider's `data` object."""
    if method == "mobile_money" and not phone_number:
        raise MarzPayError(
            "A phone number is required for mobile money collections."
        )

    # ponytail: single-market MVP — country is a fixed setting, not
    # inferred per attendee. Add phone-prefix or explicit-country
    # resolution when Tuviora expands past Uganda.
    resolved_country = country or getattr(
        settings, "MARZPAY_DEFAULT_COUNTRY", "UG"
    )

    fields = {
        "amount": str(amount),
        "currency": currency,
        "country": resolved_country,
        "reference": reference,
        "method": method,
    }

    if phone_number:
        fields["phone_number"] = phone_number

    if description:
        fields["description"] = description[:255]

    if callback_url:
        fields["callback_url"] = callback_url

    files = {key: (None, str(value)) for key, value in fields.items()}

    try:
        response = requests.post(
            f"{_base_url()}/collect-money",
            files=files,
            headers=_auth_header(),
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.exception("MarzPay collection request failed.")
        raise MarzPayError(
            "Could not reach the payment provider. Please try again."
        ) from exc

    body = response.json() if response.content else {}

    if response.status_code >= 400 or body.get("status") != "success":
        raise MarzPayError(
            body.get("message") or "Payment could not be started."
        )

    return body["data"]


def get_transaction(transaction_id):
    try:
        response = requests.get(
            f"{_base_url()}/transactions/{transaction_id}",
            headers=_auth_header(),
            timeout=15,
        )
    except requests.RequestException as exc:
        raise MarzPayError(
            "Could not reach the payment provider."
        ) from exc

    if response.status_code >= 400:
        raise MarzPayError("Transaction could not be retrieved.")

    return response.json()


def verify_webhook_signature(raw_body, timestamp, signature_header, secret):
    """Verify a MarzPay webhook's `t={ts},v1={hex}` signature header."""
    if not timestamp or not signature_header or not secret:
        return False

    parts = dict(
        part.split("=", 1)
        for part in signature_header.split(",")
        if "=" in part
    )
    provided = parts.get("v1", "")

    if not provided:
        return False

    if isinstance(raw_body, str):
        raw_body = raw_body.encode()

    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, provided)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.events.test_marzpay_service -v 2`
Expected: PASS (8 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/apps/events/services/marzpay_service.py backend/config/settings.py .env.example backend/apps/events/test_marzpay_service.py
git commit -m "feat(events): add MarzPay collections service and webhook verification"
```

---

### Task 3: Initiate-payment endpoint

**Files:**
- Create: `backend/apps/events/payment_serializers.py`
- Create: `backend/apps/events/payment_views.py` (only `InitiateRegistrationPaymentView` in this task — `MarzPayWebhookView` is added in Task 4)
- Modify: `backend/apps/events/urls.py`
- Test: `backend/apps/events/test_payments_api.py` (append)

**Interfaces:**
- Consumes: `Payment`, `EventRegistration` (Task 1), `initiate_collection`, `MarzPayError` (Task 2), `validate_phone_number` from `apps/events/services/sms_service.py` (already exists).
- Produces: `PaymentSerializer` (fields `id, registration, reference, method, amount, currency, status, redirect_url, created_at, updated_at`), `POST /api/events/<event_id>/registrations/me/pay/` body `{"method": "mobile_money"|"card", "phone_number"?: "+256..."}` → `201` with the `Payment`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/events/test_payments_api.py`:

```python
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.services.marzpay_service import MarzPayError


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
```

`Payment`, `TicketType`, `Event`, `EventRegistration`, `User`, `Decimal`, `timedelta`, `timezone` are already imported at the top of this file from Task 1. Add one more import line for `override_settings` (used by the `@override_settings(SMS_ENABLED=False)` decorator above): change `from django.test import TestCase` to `from django.test import TestCase, override_settings`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.events.test_payments_api -v 2`
Expected: new tests FAIL (404 — endpoint doesn't exist yet); Task 1's model tests still PASS.

- [ ] **Step 3: Write the serializer**

`backend/apps/events/payment_serializers.py`:

```python
from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "registration",
            "reference",
            "method",
            "amount",
            "currency",
            "status",
            "redirect_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
```

- [ ] **Step 4: Write the view**

`backend/apps/events/payment_views.py`:

```python
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EventRegistration, Payment
from .payment_serializers import PaymentSerializer
from .services.marzpay_service import MarzPayError, initiate_collection
from .services.sms_service import validate_phone_number


class InitiateRegistrationPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        registration = get_object_or_404(
            EventRegistration,
            event_id=event_id,
            user=request.user,
        )

        if registration.status != EventRegistration.Status.PAYMENT_PENDING:
            return Response(
                {"detail": "No payment is due for this registration."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        method = request.data.get("method", "mobile_money")

        if method not in (
            Payment.Method.MOBILE_MONEY,
            Payment.Method.CARD,
        ):
            return Response(
                {"detail": "Choose a supported payment method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone_number = ""

        if method == Payment.Method.MOBILE_MONEY:
            try:
                phone_number = validate_phone_number(
                    request.data.get("phone_number", "")
                )
            except ValueError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        reference = str(uuid.uuid4())

        payment = Payment.objects.create(
            registration=registration,
            reference=reference,
            method=method,
            phone_number=phone_number,
            amount=registration.amount_due,
            currency=registration.currency,
        )

        try:
            data = initiate_collection(
                amount=registration.amount_due,
                currency=registration.currency,
                reference=reference,
                method=method,
                phone_number=phone_number or None,
                description=(
                    f"{registration.event.name} registration"
                )[:255],
                callback_url=(
                    getattr(settings, "MARZPAY_CALLBACK_URL", "") or None
                ),
            )
        except MarzPayError as exc:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        transaction = data.get("transaction", {})
        payment.provider_transaction_id = transaction.get("uuid", "")
        payment.status = (
            transaction.get("status") or Payment.Status.PROCESSING
        )
        payment.redirect_url = data.get("redirect_url", "")
        payment.raw_response = data
        payment.save(
            update_fields=[
                "provider_transaction_id",
                "status",
                "redirect_url",
                "raw_response",
                "updated_at",
            ]
        )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )
```

- [ ] **Step 5: Wire the URL**

In `backend/apps/events/urls.py`, add to imports:

```python
from .payment_views import InitiateRegistrationPaymentView
```

Add to `urlpatterns`, next to the other `registrations/me/...` routes:

```python
    path(
        "<int:event_id>/registrations/me/pay/",
        InitiateRegistrationPaymentView.as_view(),
        name="initiate-registration-payment",
    ),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.events.test_payments_api -v 2`
Expected: PASS (7 tests total: 2 from Task 1 + 5 new)

- [ ] **Step 7: Commit**

```bash
git add backend/apps/events/payment_serializers.py backend/apps/events/payment_views.py backend/apps/events/urls.py backend/apps/events/test_payments_api.py
git commit -m "feat(events): add endpoint to initiate a MarzPay payment for a registration"
```

---

### Task 4: MarzPay webhook — confirm registration and record the transaction

**Files:**
- Modify: `backend/apps/events/payment_views.py` (add `MarzPayWebhookView`)
- Modify: `backend/config/urls.py`
- Test: `backend/apps/events/test_payments_api.py` (append)

**Interfaces:**
- Consumes: `verify_webhook_signature` (Task 2), `send_event_sms` (existing, `apps/events/services/event_sms_notifications.py`).
- Produces: `POST /api/payments/marzpay/webhook/` — public, HMAC-verified. On `collection.completed` for a known `reference`, flips the matching `EventRegistration` from `payment_pending` to `confirmed` and sends a confirmation SMS.

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/events/test_payments_api.py`:

```python
import hashlib
import hmac
import json


@override_settings(
    SMS_ENABLED=False, MARZPAY_WEBHOOK_SECRET="test-webhook-secret"
)
class MarzPayWebhookAPITests(APITestCase):
    def setUp(self):
        organizer = User.objects.create_user(
            username="webhook_organizer", password="TestPassword123!"
        )
        attendee = User.objects.create_user(
            username="webhook_attendee", password="TestPassword123!"
        )
        event = Event.objects.create(
            organizer=organizer,
            name="Tuviora Webhook Test",
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
        self.payment = Payment.objects.create(
            registration=self.registration,
            reference="webhook-ref-1",
            method=Payment.Method.MOBILE_MONEY,
            phone_number="+256700123456",
            amount=ticket.price,
            currency=ticket.currency,
            status=Payment.Status.PROCESSING,
        )
        self.webhook_url = "/api/payments/marzpay/webhook/"

    def _post_signed(self, payload):
        body = json.dumps(payload).encode()
        timestamp = "1700000000"
        digest = hmac.new(
            b"test-webhook-secret",
            f"{timestamp}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()

        return self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_MARZPAY_TIMESTAMP=timestamp,
            HTTP_X_MARZPAY_SIGNATURE=f"t={timestamp},v1={digest}",
        )

    def test_completed_collection_confirms_registration(self):
        response = self._post_signed(
            {
                "event_type": "collection.completed",
                "transaction": {
                    "uuid": "provider-uuid-1",
                    "reference": "webhook-ref-1",
                    "status": "completed",
                },
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.registration.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(
            self.registration.status, EventRegistration.Status.CONFIRMED
        )
        self.assertEqual(self.payment.status, "completed")
        self.assertEqual(
            self.payment.provider_transaction_id, "provider-uuid-1"
        )

    def test_failed_collection_does_not_confirm_registration(self):
        response = self._post_signed(
            {
                "event_type": "collection.failed",
                "transaction": {
                    "uuid": "provider-uuid-2",
                    "reference": "webhook-ref-1",
                    "status": "failed",
                },
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.registration.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(
            self.registration.status,
            EventRegistration.Status.PAYMENT_PENDING,
        )
        self.assertEqual(self.payment.status, "failed")

    def test_invalid_signature_is_rejected(self):
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(
                {
                    "event_type": "collection.completed",
                    "transaction": {"reference": "webhook-ref-1"},
                }
            ).encode(),
            content_type="application/json",
            HTTP_X_MARZPAY_TIMESTAMP="1700000000",
            HTTP_X_MARZPAY_SIGNATURE="t=1700000000,v1=deadbeef",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.registration.refresh_from_db()
        self.assertEqual(
            self.registration.status,
            EventRegistration.Status.PAYMENT_PENDING,
        )

    def test_unknown_reference_is_acknowledged_without_error(self):
        response = self._post_signed(
            {
                "event_type": "collection.completed",
                "transaction": {
                    "uuid": "provider-uuid-3",
                    "reference": "no-such-reference",
                    "status": "completed",
                },
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.events.test_payments_api -v 2`
Expected: new tests FAIL (404 — webhook URL doesn't exist yet).

- [ ] **Step 3: Add the webhook view**

Append to `backend/apps/events/payment_views.py` (add these imports to the existing import block at the top, then the new class at the end):

```python
import logging

from django.db import transaction as db_transaction
from rest_framework.permissions import AllowAny

from .services.event_sms_notifications import send_event_sms
from .services.marzpay_service import verify_webhook_signature

logger = logging.getLogger(__name__)
```

```python
def _send_payment_confirmation_sms(payment):
    event_name = payment.registration.event.name
    message = (
        f"Tuviora: Payment received for {event_name}. "
        "Your registration is confirmed."
    )
    send_event_sms([payment.registration.user_id], message)


class MarzPayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        timestamp = request.headers.get("X-MarzPay-Timestamp", "")
        signature = request.headers.get("X-MarzPay-Signature", "")
        secret = getattr(settings, "MARZPAY_WEBHOOK_SECRET", "")

        if not verify_webhook_signature(
            request.body, timestamp, signature, secret
        ):
            logger.warning(
                "Rejected MarzPay webhook with invalid signature."
            )
            return Response(status=status.HTTP_400_BAD_REQUEST)

        payload = request.data
        event_type = payload.get("event_type", "")
        transaction_payload = payload.get("transaction", {})
        reference = transaction_payload.get("reference", "")
        newly_confirmed = False

        with db_transaction.atomic():
            payment = (
                Payment.objects.select_for_update()
                .filter(reference=reference)
                .first()
            )

            if payment is None:
                logger.warning(
                    "MarzPay webhook for unknown reference %s.",
                    reference,
                )
                return Response(status=status.HTTP_200_OK)

            payment.provider_transaction_id = transaction_payload.get(
                "uuid", payment.provider_transaction_id
            )
            payment.status = transaction_payload.get(
                "status", payment.status
            )
            payment.raw_response = payload
            payment.save(
                update_fields=[
                    "provider_transaction_id",
                    "status",
                    "raw_response",
                    "updated_at",
                ]
            )

            if event_type == "collection.completed":
                registration = payment.registration
                if (
                    registration.status
                    == EventRegistration.Status.PAYMENT_PENDING
                ):
                    registration.status = (
                        EventRegistration.Status.CONFIRMED
                    )
                    registration.save(
                        update_fields=["status", "updated_at"]
                    )
                    newly_confirmed = True

        if newly_confirmed:
            _send_payment_confirmation_sms(payment)

        return Response(status=status.HTTP_200_OK)
```

- [ ] **Step 4: Wire the URL**

In `backend/config/urls.py`, add to imports:

```python
from apps.events.payment_views import MarzPayWebhookView
```

Add to `urlpatterns` (anywhere; grouping it near `api/events/` is fine):

```python
    path(
        "api/payments/marzpay/webhook/",
        MarzPayWebhookView.as_view(),
        name="marzpay-webhook",
    ),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.events.test_payments_api -v 2`
Expected: PASS (11 tests total)

- [ ] **Step 6: Commit**

```bash
git add backend/apps/events/payment_views.py backend/config/urls.py backend/apps/events/test_payments_api.py
git commit -m "feat(events): confirm registrations from the MarzPay payment webhook"
```

---

### Task 5: Frontend — real payment flow

**Files:**
- Modify: `frontend/src/lib/events.js`
- Modify: `frontend/src/pages/PublicEventDetail.jsx`

**Interfaces:**
- Consumes: `POST /api/events/<event_id>/registrations/me/pay/` (Task 3), `GET /api/events/<event_id>/registrations/me/` (existing, used for polling).
- Replaces the "Payment collection is coming soon" placeholder banner added by the ticketing plan's Task 6 with a working payment form.

- [ ] **Step 1: Add the API client function**

In `frontend/src/lib/events.js`, add after `registerForEvent`:

```js
export function initiateRegistrationPayment(eventId, { method, phoneNumber }) {
  return apiRequest(`/api/events/${eventId}/registrations/me/pay/`, {
    method: 'POST',
    body: JSON.stringify({
      method,
      ...(phoneNumber ? { phone_number: phoneNumber } : {}),
    }),
  })
}
```

- [ ] **Step 2: Add payment state and handlers**

In `frontend/src/pages/PublicEventDetail.jsx`, add to the imports:

```js
import { registerForEvent, getMyEventRegistration, cancelMyEventRegistration, initiateRegistrationPayment } from '../lib/events'
```

Add state next to `selectedTicketTypeId`:

```js
  const [paymentMethod, setPaymentMethod] = useState('mobile_money')
  const [paymentPhone, setPaymentPhone] = useState('')
  const [paymentError, setPaymentError] = useState('')
  const [payingNow, setPayingNow] = useState(false)
  const [polling, setPolling] = useState(false)
```

Add a polling effect next to the other `useEffect` hooks:

```js
  useEffect(() => {
    if (!polling) return undefined

    const interval = setInterval(async () => {
      try {
        const latest = await getMyEventRegistration(eventId)
        setRegistration(latest)
        if (latest.status !== 'payment_pending') {
          setPolling(false)
        }
      } catch {
        // Keep polling; a transient error shouldn't stop the check.
      }
    }, 4000)

    return () => clearInterval(interval)
  }, [polling, eventId])
```

Add a submit handler next to `handleRegister`:

```js
  async function handlePay() {
    setPayingNow(true)
    setPaymentError('')

    try {
      const payment = await initiateRegistrationPayment(eventId, {
        method: paymentMethod,
        phoneNumber: paymentMethod === 'mobile_money' ? paymentPhone : undefined,
      })

      if (payment.redirect_url) {
        window.location.href = payment.redirect_url
        return
      }

      setPolling(true)
    } catch (err) {
      setPaymentError(err.message || 'Unable to start payment. Please try again.')
    } finally {
      setPayingNow(false)
    }
  }
```

- [ ] **Step 3: Replace the placeholder banner**

Replace the block added by the ticketing plan:

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

with:

```jsx
                    {registration?.status === 'payment_pending' ? (
                      <div className="mt-6 space-y-4">
                        <div
                          role="status"
                          className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
                        >
                          Your spot is reserved — complete payment of{' '}
                          {registration.amount_due} {registration.currency}{' '}
                          to confirm it.
                        </div>

                        {polling && (
                          <p role="status" className="text-sm text-[#647064]">
                            Waiting for payment confirmation...
                          </p>
                        )}

                        <div className="flex gap-4">
                          <label className="flex items-center gap-2">
                            <input
                              type="radio"
                              checked={paymentMethod === 'mobile_money'}
                              onChange={() => setPaymentMethod('mobile_money')}
                            />
                            Mobile Money
                          </label>
                          <label className="flex items-center gap-2">
                            <input
                              type="radio"
                              checked={paymentMethod === 'card'}
                              onChange={() => setPaymentMethod('card')}
                            />
                            Card
                          </label>
                        </div>

                        {paymentMethod === 'mobile_money' && (
                          <input
                            value={paymentPhone}
                            onChange={(event) => setPaymentPhone(event.target.value)}
                            placeholder="+256700123456"
                            className="w-full rounded-xl border border-[#DCE5D8] bg-white px-4 py-3"
                          />
                        )}

                        <button
                          type="button"
                          onClick={handlePay}
                          disabled={payingNow || polling}
                          className="w-full rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white hover:bg-[#31563A] disabled:opacity-60"
                        >
                          {payingNow
                            ? 'Starting payment...'
                            : paymentMethod === 'card'
                              ? 'Pay by card'
                              : 'Send payment prompt'}
                        </button>

                        {paymentError && (
                          <p role="alert" className="text-sm text-red-700">
                            {paymentError}
                          </p>
                        )}
                      </div>
                    ) : registration?.status === 'confirmed' ? (
```

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev` and `cd backend && python manage.py runserver` together, with `MARZPAY_API_KEY`/`MARZPAY_API_SECRET` set to real sandbox credentials in `backend/.env`.
1. Register for a paid event, land on the `payment_pending` payment form.
2. Choose Mobile Money, enter a sandbox test number, submit — confirm a `Payment` row appears (Django admin or shell) with `status="processing"` and the UI shows "Waiting for payment confirmation...".
3. From a local tunnel (e.g. `ngrok`) pointed at the Django dev server, set `MARZPAY_CALLBACK_URL` to the tunnel's `/api/payments/marzpay/webhook/` URL and trigger a sandbox completion from MarzPay's dashboard — confirm the registration flips to `confirmed` within one poll interval and the attendee (if SMS-opted-in) receives the confirmation text.
4. Choose Card instead — confirm the browser redirects to a `wallet.wearemarz.com` checkout URL.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/events.js frontend/src/pages/PublicEventDetail.jsx
git commit -m "feat(frontend): collect MarzPay payments for paid registrations"
```
