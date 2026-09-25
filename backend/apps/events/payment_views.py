import uuid

from django.conf import settings
from django.db import transaction
from django.http import Http404
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
                    {
                        "detail": (
                            "A payment is already in progress for this "
                            "registration."
                        )
                    },
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
