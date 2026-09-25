from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EventRegistration, RegistrationTicket


class MyRegistrationTicketView(APIView):
    """Issue or retrieve the authenticated attendee's confirmed ticket."""

    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        with transaction.atomic():
            registration = get_object_or_404(
                EventRegistration.objects.select_for_update(),
                event_id=event_id,
                user=request.user,
            )

            if registration.status != EventRegistration.Status.CONFIRMED:
                return Response(
                    {
                        "detail": (
                            "A ticket is available only for a "
                            "confirmed registration."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            ticket, _ = RegistrationTicket.objects.get_or_create(
                registration=registration,
            )

            return Response(
                {
                    "reference": str(ticket.reference),
                    "qr_token": str(ticket.qr_token),
                    "event_id": registration.event_id,
                    "registration_id": registration.id,
                    "checked_in": ticket.checked_in_at is not None,
                    "checked_in_at": ticket.checked_in_at,
                }
            )
