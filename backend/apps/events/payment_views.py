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
