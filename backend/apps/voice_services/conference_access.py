"""Issue and redeem private conference access codes."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .conference import can_join_conference
from .models import ConferenceAccessCode, EventConference


CODE_LIFETIME = timedelta(minutes=10)


class ConferenceAccessError(Exception):
    """A conference access request cannot be completed."""


def hash_access_code(code):
    """Use a keyed hash so database access alone cannot reveal short PINs."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


@transaction.atomic
def issue_access_code(event, user):
    """Issue a short-lived code to an authorized event team member."""
    if not can_join_conference(event, user):
        raise ConferenceAccessError("Conference access denied.")

    try:
        conference = EventConference.objects.select_for_update().get(
            event=event,
            status=EventConference.Status.ACTIVE,
        )
    except EventConference.DoesNotExist as exc:
        raise ConferenceAccessError(
            "The conference is not active."
        ) from exc

    # Revoke previously issued, unused codes for this user and conference.
    ConferenceAccessCode.objects.filter(
        conference=conference,
        user=user,
        used_at__isnull=True,
    ).delete()

    # Check for collisions before inserting. A unique database
    # constraint provides an additional safeguard.
    for _ in range(5):
        code = f"{secrets.randbelow(100_000_000):08d}"
        code_hash = hash_access_code(code)

        if ConferenceAccessCode.objects.filter(
            code_hash=code_hash,
        ).exists():
            continue

        ConferenceAccessCode.objects.create(
            conference=conference,
            user=user,
            code_hash=code_hash,
            expires_at=timezone.now() + CODE_LIFETIME,
        )

        return code

    raise ConferenceAccessError(
        "Unable to generate a unique access code. Please retry."
    )


@transaction.atomic
def redeem_access_code(code):
    """Consume a valid code and return the authorized conference and user."""
    if not isinstance(code, str) or len(code) != 8 or not code.isascii() or not code.isdigit():
        raise ConferenceAccessError("Invalid access code.")

    try:
        credential = (
            ConferenceAccessCode.objects
            .select_for_update()
            .select_related("conference__event", "user")
            .get(code_hash=hash_access_code(code))
        )
    except ConferenceAccessCode.DoesNotExist as exc:
        raise ConferenceAccessError("Invalid access code.") from exc

    now = timezone.now()

    if credential.used_at is not None or credential.expires_at <= now:
        raise ConferenceAccessError("Invalid or expired access code.")

    conference = credential.conference

    if conference.status != EventConference.Status.ACTIVE:
        raise ConferenceAccessError("The conference is not active.")

    if not can_join_conference(conference.event, credential.user):
        raise ConferenceAccessError("Conference access denied.")

    # Consume the PIN with a conditional database update.
    # Only one request can successfully change it from unused to used.
    updated = ConferenceAccessCode.objects.filter(
        pk=credential.pk,
        used_at__isnull=True,
        expires_at__gt=now,
    ).update(used_at=now)

    if updated != 1:
        raise ConferenceAccessError(
            "Invalid or expired access code."
        )

    return conference, credential.user
