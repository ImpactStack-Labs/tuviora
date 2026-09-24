from django.db import IntegrityError, OperationalError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, EventRegistration
from .registration_serializers import (
    EventRegistrationSerializer,
    MyRegistrationsSerializer,
)


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

                existing = EventRegistration.objects.filter(
                    event=event,
                    user=request.user,
                ).first()

                if existing and existing.status == (
                    EventRegistration.Status.CONFIRMED
                ):
                    return Response(
                        {"detail": "You are already registered."},
                        status=status.HTTP_409_CONFLICT,
                    )

                confirmed_count = (
                    EventRegistration.objects.filter(
                        event=event,
                        status=EventRegistration.Status.CONFIRMED,
                    ).count()
                )

                if (
                    event.capacity is not None
                    and confirmed_count >= event.capacity
                ):
                    return Response(
                        {"detail": "This event is fully booked."},
                        status=status.HTTP_409_CONFLICT,
                    )

                if existing:
                    existing.status = (
                        EventRegistration.Status.CONFIRMED
                    )
                    existing.save(
                        update_fields=["status", "updated_at"]
                    )
                    registration = existing
                else:
                    registration = EventRegistration.objects.create(
                        event=event,
                        user=request.user,
                    )

        except IntegrityError:
            return Response(
                {"detail": "Registration conflict. Please retry."},
                status=status.HTTP_409_CONFLICT,
            )
        except OperationalError:
            return Response(
                {"detail": "Registration is busy. Please retry."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

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
            .order_by("-registered_at", "-id")
        )

        return Response(
            MyRegistrationsSerializer(registrations, many=True).data
        )
