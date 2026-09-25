import logging
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EventRegistration, Payment
from .payment_serializers import PaymentSerializer
from .services.event_sms_notifications import send_event_sms
from .services.marzpay_service import (
    MarzPayError,
    MarzPayUnavailable,
    initiate_collection,
    verify_webhook_signature,
)
from .services.sms_service import validate_phone_number

logger = logging.getLogger(__name__)

PAYMENT_IN_PROGRESS_DETAIL = (
    "A payment is already in progress for this registration."
)


class InitiateRegistrationPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        # Lock the registration row for the status check + Payment creation
        # so two concurrent requests can't both pass the PAYMENT_PENDING
        # check and each fire a separate MarzPay collection. The lock is
        # released when this block commits, *before* the network call below.
        with transaction.atomic():
            try:
                registration = EventRegistration.objects.select_for_update().get(
                    event_id=event_id,
                    user=request.user,
                )
            except EventRegistration.DoesNotExist:
                raise Http404("No registration matches the given query.")

            if registration.status != EventRegistration.Status.PAYMENT_PENDING:
                return Response(
                    {"detail": "No payment is due for this registration."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Guard against a second (now-serialized) request creating its
            # own Payment for this registration while an earlier attempt is
            # still in flight. registration.status alone can't catch this,
            # since this view never writes it. FAILED/CANCELLED are
            # terminal and must not block a retry.
            if registration.payments.filter(
                status__in=[Payment.Status.PENDING, Payment.Status.PROCESSING]
            ).exists():
                return Response(
                    {"detail": PAYMENT_IN_PROGRESS_DETAIL},
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

            # Nested atomic (savepoint): on a DB where select_for_update()
            # above doesn't actually lock (e.g. sqlite), two concurrent
            # requests can both pass the .exists() check and both reach
            # this INSERT. The one_payment_in_progress_per_registration
            # constraint (Payment.Meta) rejects the loser with an
            # IntegrityError; the savepoint keeps that failure from
            # poisoning the outer transaction so we can still respond
            # cleanly instead of 500ing.
            try:
                with transaction.atomic():
                    payment = Payment.objects.create(
                        registration=registration,
                        reference=reference,
                        method=method,
                        phone_number=phone_number,
                        amount=registration.amount_due,
                        currency=registration.currency,
                    )
            except IntegrityError:
                return Response(
                    {"detail": PAYMENT_IN_PROGRESS_DETAIL},
                    status=status.HTTP_400_BAD_REQUEST,
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
        except MarzPayUnavailable as exc:
            # ponytail: we genuinely don't know whether MarzPay received
            # this request, so we leave the payment PENDING instead of
            # FAILED — marking it FAILED would let the in-progress gate
            # above wave through a retry while the first attempt might
            # still be live on MarzPay's side, risking a double charge.
            # Deferred upgrade path: get_transaction() (already written,
            # unused) could reconcile this automatically; for now an
            # operator resolves a stuck row via Django admin (Payment).
            logger.warning(
                "MarzPay unavailable for payment %s: %s", payment.reference, exc
            )
            return Response(
                {
                    "detail": (
                        "We're confirming this payment with the provider. "
                        "Please wait a moment before trying again."
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except MarzPayError as exc:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        provider_transaction = data.get("transaction", {})
        payment.provider_transaction_id = provider_transaction.get("uuid", "")
        payment.status = (
            provider_transaction.get("status") or Payment.Status.PROCESSING
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

        with transaction.atomic():
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
                # Lock the registration row too: it's a different table from
                # Payment, so without this a concurrent
                # InitiateRegistrationPaymentView call touching the same
                # registration through another Payment row would never
                # contend with this transaction's Payment-row lock.
                registration = EventRegistration.objects.select_for_update().get(
                    pk=payment.registration_id
                )
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
