"""Bind verified conference access to a specific telephone call."""

import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache

from .conference_access import (
    ConferenceAccessError,
    redeem_access_code,
)
from .conference_rate_limit import (
    check_attempt_limit,
    clear_session_failures,
    record_failed_attempt,
)
from .models import EventConference


SESSION_TTL_SECONDS = 15 * 60


def _session_key(session_id):
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("A valid call session ID is required.")

    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"conference-session:{session_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"voice_conference:verified:{digest}"


def verify_conference_caller(session_id, caller_number, code):
    """Verify a PIN and authorize only the current call session.

    Call this only after verifying the telephone provider's callback.
    """
    key = _session_key(session_id)

    # A session must not switch identities after successful verification.
    if cache.get(key) is not None:
        raise ConferenceAccessError(
            "This call has already been verified."
        )

    check_attempt_limit(session_id, caller_number)

    try:
        conference, user = redeem_access_code(code)
    except ConferenceAccessError:
        record_failed_attempt(session_id, caller_number)
        raise

    cache.set(
        key,
        {
            "conference_id": conference.pk,
            "user_id": user.pk,
            "caller_number": caller_number or "",
        },
        timeout=SESSION_TTL_SECONDS,
    )

    clear_session_failures(session_id)

    return conference, user


def get_verified_conference(session_id, caller_number):
    """Return the conference only for the verified call and caller."""
    data = cache.get(_session_key(session_id))

    if not isinstance(data, dict):
        return None

    if data.get("caller_number") != (caller_number or ""):
        return None

    try:
        conference = EventConference.objects.select_related(
            "event",
            "organizer",
        ).get(
            pk=data["conference_id"],
            status=EventConference.Status.ACTIVE,
        )
    except (EventConference.DoesNotExist, KeyError):
        return None

    from django.contrib.auth import get_user_model
    from .conference import can_join_conference

    user = get_user_model().objects.filter(
        pk=data.get("user_id"),
    ).first()

    if not can_join_conference(conference.event, user):
        return None

    return conference, user


def clear_verified_conference(session_id):
    """Remove a call's authorization when the call ends."""
    cache.delete(_session_key(session_id))
