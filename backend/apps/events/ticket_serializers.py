from rest_framework import serializers

from .models import TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TicketType
        fields = [
            "id",
            "event",
            "name",
            "price",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "event", "created_at", "updated_at"]
