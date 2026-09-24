import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailVerification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verifications",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user):
        token = secrets.token_urlsafe(32)

        verification = cls.objects.create(
            user=user,
            token_hash=hashlib.sha256(
                token.encode("utf-8")
            ).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=24),
        )

        return verification, token

    def __str__(self):
        return f"Email verification for user {self.user_id}"
