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
