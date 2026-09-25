from django.db import models

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Event,
    EventMembership,
    EventRegistration,
    RegistrationTicket,
)


class TicketCheckInSerializer(serializers.Serializer):
    token = serializers.UUIDField()


class TicketCheckInView(APIView):
    """Check in an attendee using a QR token or ticket reference."""

    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        serializer = TicketCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        with transaction.atomic():
            event = get_object_or_404(Event, pk=event_id)

            authorized = (
                event.organizer_id == request.user.pk
                or EventMembership.objects.filter(
                    event=event,
                    user=request.user,
                ).exists()
            )

            if not authorized:
                return Response(
                    {"detail": "You cannot check in attendees for this event."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            ticket = (
                RegistrationTicket.objects
                .select_for_update()
                .select_related("registration", "registration__user")
                .filter(registration__event=event)
                .filter(
                    models.Q(qr_token=token)
                    | models.Q(reference=token)
                )
                .first()
            )

            if ticket is None:
                return Response(
                    {"detail": "Ticket not found for this event."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if ticket.registration.status != EventRegistration.Status.CONFIRMED:
                return Response(
                    {"detail": "This registration is not confirmed."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if ticket.checked_in_at is not None:
                return Response(
                    {
                        "detail": "This ticket has already been checked in.",
                        "checked_in_at": ticket.checked_in_at,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            ticket.checked_in_at = timezone.now()
            ticket.checked_in_by = request.user
            ticket.save(update_fields=["checked_in_at", "checked_in_by"])

            return Response(
                {
                    "detail": "Attendee checked in successfully.",
                    "reference": str(ticket.reference),
                    "attendee": ticket.registration.user.get_full_name()
                    or ticket.registration.user.username,
                    "checked_in_at": ticket.checked_in_at,
                }
            )
