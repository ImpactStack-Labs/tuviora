from rest_framework import serializers

from .models import EventRegistration
from .public_serializers import PublicEventSerializer


class EventRegistrationSerializer(serializers.ModelSerializer):
    """Read-only representation of an attendee registration."""

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "event",
            "user",
            "ticket_type",
            "amount_due",
            "currency",
            "status",
            "registered_at",
            "updated_at",
        ]
        read_only_fields = fields



class MyRegistrationsSerializer(serializers.ModelSerializer):
    """An attendee's registration with public event information."""

    event = PublicEventSerializer(read_only=True)

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "event",
            "ticket_type",
            "amount_due",
            "currency",
            "status",
            "registered_at",
            "updated_at",
        ]
        read_only_fields = fields
