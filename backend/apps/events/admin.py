from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "event_format",
        "date",
        "status",
        "organizer",
        "capacity",
        "created_at",
    )

    list_filter = (
        "category",
        "event_format",
        "status",
        "date",
    )

    search_fields = (
        "name",
        "venue",
        "organizer__username",
        "organizer__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )