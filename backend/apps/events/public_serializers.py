from rest_framework import serializers

from .models import Event


class PublicEventSerializer(serializers.ModelSerializer):
    """Public information available before registration."""

    ticket_types = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "category",
            "description",
            "date",
            "timezone_name",
            "start_time",
            "end_time",
            "event_format",
            "venue",
            "landmark",
            "capacity",
            "ticket_types",
        ]
        read_only_fields = [
            "id",
            "name",
            "category",
            "description",
            "date",
            "timezone_name",
            "start_time",
            "end_time",
            "event_format",
            "venue",
            "landmark",
            "capacity",
        ]

    def get_ticket_types(self, obj):
        from .ticket_serializers import TicketTypeSerializer

        active = [t for t in obj.ticket_types.all() if t.is_active]
        return TicketTypeSerializer(active, many=True).data
