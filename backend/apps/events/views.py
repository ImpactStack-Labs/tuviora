from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Event, Incident, ReadinessTask
from .serializers import (
    EventSerializer,
    IncidentSerializer,
    ReadinessTaskSerializer,
)


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Event.objects
            .filter(organizer=self.request.user)
            .select_related("organizer")
        )

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)


class EventTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = ReadinessTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return get_object_or_404(
            Event,
            id=self.kwargs["event_id"],
            organizer=self.request.user,
        )

    def get_queryset(self):
        event = self.get_event()

        return (
            ReadinessTask.objects
            .filter(event=event)
            .select_related("event", "assignee")
        )

    def perform_create(self, serializer):
        serializer.save(event=self.get_event())


class EventTaskDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ReadinessTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ReadinessTask.objects
            .filter(event__id=self.kwargs["event_id"])
            .filter(event__organizer=self.request.user)
            .select_related("event", "assignee")
        )


class EventIncidentListCreateView(generics.ListCreateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return get_object_or_404(
            Event,
            id=self.kwargs["event_id"],
            organizer=self.request.user,
        )

    def get_queryset(self):
        event = self.get_event()

        return (
            Incident.objects
            .filter(event=event)
            .select_related("event", "reported_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            event=self.get_event(),
            reported_by=self.request.user,
        )


class EventIncidentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Incident.objects
            .filter(event__id=self.kwargs["event_id"])
            .filter(event__organizer=self.request.user)
            .select_related("event", "reported_by")
        )
