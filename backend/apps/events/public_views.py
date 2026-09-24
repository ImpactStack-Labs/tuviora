from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Event
from .public_serializers import PublicEventSerializer


class PublicEventListView(generics.ListAPIView):
    """List published events that have not passed their event date."""

    serializer_class = PublicEventSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return (
            Event.objects
            .filter(
                status=Event.Status.PUBLISHED,
                date__gte=timezone.localdate(),
            )
            .order_by("date", "start_time", "id")
            .prefetch_related("ticket_types")
        )

class PublicEventDetailView(generics.RetrieveAPIView):
    """Retrieve one published event whose event date has not passed."""

    serializer_class = PublicEventSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return Event.objects.filter(
            status=Event.Status.PUBLISHED,
            date__gte=timezone.localdate(),
        ).prefetch_related("ticket_types")
