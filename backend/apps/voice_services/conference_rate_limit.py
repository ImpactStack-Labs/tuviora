"""Rate limits for private telephone conference PIN verification."""

import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache


MAX_SESSION_FAILURES = 5
MAX_CALLER_FAILURES = 10
LOCKOUT_SECONDS = 15 * 60


class ConferenceRateLimitError(Exception):
    """Too many unsuccessful conference access attempts."""


def _key(category, identifier):
    """Avoid storing caller numbers or session IDs directly in cache keys."""
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("A valid identifier is required.")

    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{category}:{identifier}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"voice_conference:failures:{category}:{digest}"


def check_attempt_limit(session_id, caller_number):
    """Reject attempts when either limit has been reached."""
    session_key = _key("session", session_id)

    if cache.get(session_key, 0) >= MAX_SESSION_FAILURES:
        raise ConferenceRateLimitError(
            "Too many attempts for this call."
        )

    if caller_number:
        caller_key = _key("caller", caller_number)

        if cache.get(caller_key, 0) >= MAX_CALLER_FAILURES:
            raise ConferenceRateLimitError(
                "Too many attempts for this caller."
            )


def record_failed_attempt(session_id, caller_number):
    """Record a failed PIN attempt against the session and caller."""
    identifiers = [("session", session_id)]

    if caller_number:
        identifiers.append(("caller", caller_number))

    for category, identifier in identifiers:
        key = _key(category, identifier)

        # cache.add is atomic on supported shared cache backends.
        if cache.add(key, 1, timeout=LOCKOUT_SECONDS):
            continue

        try:
            cache.incr(key)
        except ValueError:
            # The entry may have expired between add and incr.
            cache.add(key, 1, timeout=LOCKOUT_SECONDS)


def clear_session_failures(session_id):
    """Clear session failures after successful verification."""
    cache.delete(_key("session", session_id))
