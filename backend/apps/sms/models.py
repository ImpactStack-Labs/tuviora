from django.conf import settings
from django.db import models


class SMSPreference(models.Model):
    """A user's phone number and permission to receive SMS."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sms_preference",
    )
    phone_number = models.CharField(
        max_length=16,
        blank=True,
    )
    sms_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Moved from apps.accounts without a data migration — keep pointing
        # at the table Django already created there.
        db_table = "accounts_smspreference"

    def __str__(self):
        return f"SMS preferences for user {self.user_id}"
