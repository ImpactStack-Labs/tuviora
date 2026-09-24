from rest_framework import serializers

from .models import EventRegistration


class EventRegistrationSerializer(serializers.ModelSerializer):
    """Read-only representation of an attendee registration."""

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "event",
            "user",
            "status",
            "registered_at",
            "updated_at",
        ]
        read_only_fields = fields
