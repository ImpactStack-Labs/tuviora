from django.contrib import admin

from .models import Event, Payment


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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "registration",
        "method",
        "amount",
        "currency",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "method",
    )

    search_fields = (
        "reference",
        "provider_transaction_id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )