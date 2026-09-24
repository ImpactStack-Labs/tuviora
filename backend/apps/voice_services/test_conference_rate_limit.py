"""Tests for conference PIN attempt limits."""

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from .conference_rate_limit import (
    ConferenceRateLimitError,
    check_attempt_limit,
    clear_session_failures,
    record_failed_attempt,
)


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "conference-rate-limit-tests",
    }
}


@override_settings(CACHES=TEST_CACHES)
class ConferenceRateLimitTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_session_blocks_after_five_failures(self):
        for _ in range(5):
            check_attempt_limit("session-1", None)
            record_failed_attempt("session-1", None)

        with self.assertRaises(ConferenceRateLimitError):
            check_attempt_limit("session-1", None)

    def test_four_failures_do_not_block_session(self):
        for _ in range(4):
            record_failed_attempt("session-2", None)

        check_attempt_limit("session-2", None)

    def test_caller_blocks_after_ten_failures(self):
        for attempt in range(10):
            session_id = f"session-{attempt}"
            check_attempt_limit(session_id, "+256700000001")
            record_failed_attempt(
                session_id,
                "+256700000001",
            )

        with self.assertRaises(ConferenceRateLimitError):
            check_attempt_limit(
                "another-session",
                "+256700000001",
            )

    def test_caller_limit_applies_across_sessions(self):
        for attempt in range(10):
            record_failed_attempt(
                f"caller-session-{attempt}",
                "+256700000002",
            )

        with self.assertRaises(ConferenceRateLimitError):
            check_attempt_limit(
                "new-session",
                "+256700000002",
            )

        # A different caller is not blocked.
        check_attempt_limit(
            "new-session",
            "+256700000003",
        )

    def test_clearing_session_does_not_clear_caller_limit(self):
        for attempt in range(10):
            record_failed_attempt(
                f"clear-session-{attempt}",
                "+256700000004",
            )

        clear_session_failures("clear-session-0")

        # The caller remains blocked across new sessions.
        with self.assertRaises(ConferenceRateLimitError):
            check_attempt_limit(
                "fresh-session",
                "+256700000004",
            )

    def test_clearing_session_allows_new_attempts(self):
        for _ in range(5):
            record_failed_attempt("session-clear", None)

        clear_session_failures("session-clear")

        check_attempt_limit("session-clear", None)

    def test_missing_session_id_is_rejected(self):
        with self.assertRaises(ValueError):
            check_attempt_limit("", None)

        with self.assertRaises(ValueError):
            record_failed_attempt("", None)
