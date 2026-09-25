from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EventAnnouncement
from .permissions import lead_event_or_deny
from .services.announcements import announce_to_attendees


class EventAnnouncementSerializer(serializers.ModelSerializer):
    message = serializers.CharField(max_length=480)
    sent_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EventAnnouncement
        fields = [
            "id",
            "message",
            "submitted",
            "failed",
            "skipped",
            "sent_by",
            "sent_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "submitted",
            "failed",
            "skipped",
            "sent_by",
            "created_at",
        ]

    def get_sent_by_name(self, obj):
        if obj.sent_by is None:
            return None
        return obj.sent_by.get_full_name() or obj.sent_by.username


class EventAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        announcements = event.announcements.select_related("sent_by")
        return Response(
            EventAnnouncementSerializer(announcements, many=True).data
        )

    def post(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        serializer = EventAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = announce_to_attendees(
            event,
            serializer.validated_data["message"],
            sent_by=request.user,
        )
        return Response(
            EventAnnouncementSerializer(announcement).data,
            status=status.HTTP_201_CREATED,
        )
