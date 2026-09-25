"""Database models for Tuviora's private event conferences."""

from django.conf import settings
from django.db import models


class EventConference(models.Model):
    """A private telephone conference belonging to one event."""

    class Status(models.TextChoices):
        READY = "ready", "Ready"
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"

    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="voice_conference",
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organized_voice_conferences",
    )

    room_name = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.READY,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.event.name} ({self.status})"


class ConferenceAccessCode(models.Model):
    """A short-lived, single-use credential for a conference caller."""

    conference = models.ForeignKey(
        EventConference,
        on_delete=models.CASCADE,
        related_name="access_codes",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conference_access_codes",
    )

    code_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["conference", "user", "expires_at"],
            ),
        ]

    def __str__(self):
        return f"Conference access for user {self.user_id}"


class PendingVoiceCall(models.Model):
    """Transient routing state linking an outbound call to its message.

    Not an audit log: one row per outstanding call attempt, written when
    we dial and deleted when the matching outbound callback claims it.
    A row nobody ever answers is simply ignored once expires_at passes.
    """

    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["phone_number", "expires_at"]),
        ]

    def __str__(self):
        return f"Pending call to {self.phone_number}"
