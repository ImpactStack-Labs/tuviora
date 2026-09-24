from rest_framework import serializers

from .models import Event


class PublicEventSerializer(serializers.ModelSerializer):
    """Public information available before registration."""

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
        ]
        read_only_fields = fields
