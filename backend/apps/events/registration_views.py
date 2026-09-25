from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, EventRegistration
from .registration_serializers import (
    EventRegistrationSerializer,
    MyRegistrationsSerializer,
)
from .services.registration import RegistrationError, register_for_event


class EventRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = get_object_or_404(
            Event, pk=event_id, organizer=request.user
        )
        registrations = (
            EventRegistration.objects
            .filter(event=event)
            .select_related("user")
            .order_by("-registered_at")
        )
        return Response(
            EventRegistrationSerializer(
                registrations, many=True
            ).data
        )

    def post(self, request, event_id):
        try:
            registration = register_for_event(
                event_id,
                request.user,
                ticket_type_id=request.data.get("ticket_type_id"),
            )
        except RegistrationError as exc:
            return Response({"detail": exc.detail}, status=exc.http_status)

        return Response(
            EventRegistrationSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )


class MyEventRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        registration = get_object_or_404(
            EventRegistration,
            event_id=event_id,
            user=request.user,
        )
        return Response(
            EventRegistrationSerializer(registration).data
        )


class CancelEventRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        with transaction.atomic():
            # Use the same lock order as registration: event first.
            get_object_or_404(
                Event.objects.select_for_update(),
                pk=event_id,
            )
            registration = get_object_or_404(
                EventRegistration.objects.select_for_update(),
                event_id=event_id,
                user=request.user,
            )

            if registration.status == (
                EventRegistration.Status.CANCELLED
            ):
                return Response(
                    {"detail": "Registration already cancelled."},
                    status=status.HTTP_409_CONFLICT,
                )

            registration.status = (
                EventRegistration.Status.CANCELLED
            )
            registration.save(
                update_fields=["status", "updated_at"]
            )

        return Response(
            EventRegistrationSerializer(registration).data
        )



class MyRegistrationsListView(APIView):
    """List only the signed-in attendee's event registrations."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        registrations = (
            EventRegistration.objects
            .filter(user=request.user)
            .select_related("event")
            .prefetch_related("event__ticket_types")
            .order_by("-registered_at", "-id")
        )

        return Response(
            MyRegistrationsSerializer(registrations, many=True).data
        )
