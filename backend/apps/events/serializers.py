from django.utils import timezone
from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    organizer = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    class Meta:
        model = Event

        fields = [
            "id",
            "name",
            "category",
            "description",
            "date",
            "start_time",
            "end_time",
            "event_format",
            "venue",
            "landmark",
            "latitude",
            "longitude",
            "online_platform",
            "online_url",
            "joining_instructions",
            "capacity",
            "organizer",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "organizer",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        event_format = attrs.get(
            "event_format",
            getattr(
                self.instance,
                "event_format",
                Event.EventFormat.PHYSICAL,
            ),
        )

        venue = attrs.get(
            "venue",
            getattr(self.instance, "venue", ""),
        )

        online_platform = attrs.get(
            "online_platform",
            getattr(self.instance, "online_platform", ""),
        )

        online_url = attrs.get(
            "online_url",
            getattr(self.instance, "online_url", ""),
        )

        event_date = attrs.get(
            "date",
            getattr(self.instance, "date", None),
        )

        start_time = attrs.get(
            "start_time",
            getattr(self.instance, "start_time", None),
        )

        end_time = attrs.get(
            "end_time",
            getattr(self.instance, "end_time", None),
        )

        if event_format in {
            Event.EventFormat.PHYSICAL,
            Event.EventFormat.HYBRID,
        }:
            if not venue:
                raise serializers.ValidationError(
                    {
                        "venue": (
                            "Venue is required for physical and "
                            "hybrid events."
                        )
                    }
                )

        if event_format in {
            Event.EventFormat.VIRTUAL,
            Event.EventFormat.HYBRID,
        }:
            if not online_platform:
                raise serializers.ValidationError(
                    {
                        "online_platform": (
                            "Online platform is required for virtual "
                            "and hybrid events."
                        )
                    }
                )

            if not online_url:
                raise serializers.ValidationError(
                    {
                        "online_url": (
                            "Online URL is required for virtual "
                            "and hybrid events."
                        )
                    }
                )

        if event_format == Event.EventFormat.VIRTUAL and venue:
            raise serializers.ValidationError(
                {
                    "venue": (
                        "Venue should not be provided for a "
                        "virtual-only event."
                    )
                }
            )

        if event_date and event_date < timezone.localdate():
            raise serializers.ValidationError(
                {
                    "date": "Event date cannot be in the past."
                }
            )

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {
                    "end_time": (
                        "End time must be later than start time."
                    )
                }
            )

        latitude = attrs.get(
            "latitude",
            getattr(self.instance, "latitude", None),
        )

        longitude = attrs.get(
            "longitude",
            getattr(self.instance, "longitude", None),
        )

        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {
                    "latitude": (
                        "Latitude and longitude must be "
                        "provided together."
                    ),
                    "longitude": (
                        "Latitude and longitude must be "
                        "provided together."
                    ),
                }
            )

        return attrs