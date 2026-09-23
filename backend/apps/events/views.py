from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Event
from .serializers import EventSerializer


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