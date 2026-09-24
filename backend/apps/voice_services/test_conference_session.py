"""Tests for conference telephone-session authorization."""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.events.models import Event, EventMembership

from .conference_access import ConferenceAccessError, issue_access_code
from .conference_rate_limit import ConferenceRateLimitError
from .conference_service import end_conference, start_conference
from .conference_session import (
    clear_verified_conference,
    get_verified_conference,
    verify_conference_caller,
)


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "conference-session-tests",
    }
}


@override_settings(CACHES=TEST_CACHES)
class ConferenceSessionTests(TestCase):

    def setUp(self):
        cache.clear()

        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="session_organizer",
            password="test-password",
        )
        self.worker = User.objects.create_user(
            username="session_worker",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Session Security Test",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        EventMembership.objects.create(
            event=self.event,
            user=self.worker,
            role=EventMembership.Role.MEMBER,
        )

        self.conference = start_conference(
            self.event,
            self.organizer,
        )

        self.phone = "+256700000101"

    def tearDown(self):
        cache.clear()

    def test_valid_code_authorizes_current_session(self):
        code = issue_access_code(self.event, self.worker)

        conference, user = verify_conference_caller(
            "call-1", self.phone, code
        )

        self.assertEqual(conference, self.conference)
        self.assertEqual(user, self.worker)

        verified = get_verified_conference(
            "call-1", self.phone
        )

        self.assertIsNotNone(verified)
        self.assertEqual(verified[1], self.worker)

    def test_other_session_is_not_authorized(self):
        code = issue_access_code(self.event, self.worker)

        verify_conference_caller(
            "call-2", self.phone, code
        )

        self.assertIsNone(
            get_verified_conference(
                "different-call", self.phone
            )
        )

    def test_different_caller_is_not_authorized(self):
        code = issue_access_code(self.event, self.worker)

        verify_conference_caller(
            "call-3", self.phone, code
        )

        self.assertIsNone(
            get_verified_conference(
                "call-3", "+256700000999"
            )
        )

    def test_same_session_cannot_switch_identity(self):
        code = issue_access_code(self.event, self.worker)

        verify_conference_caller(
            "call-4", self.phone, code
        )

        organizer_code = issue_access_code(
            self.event, self.organizer
        )

        with self.assertRaises(ConferenceAccessError):
            verify_conference_caller(
                "call-4", self.phone, organizer_code
            )

    def test_invalid_pin_counts_toward_limit(self):
        for _ in range(5):
            with self.assertRaises(ConferenceAccessError):
                verify_conference_caller(
                    "call-5", self.phone, "00000000"
                )

        valid_code = issue_access_code(
            self.event, self.worker
        )

        with self.assertRaises(ConferenceRateLimitError):
            verify_conference_caller(
                "call-5", self.phone, valid_code
            )

    def test_removed_worker_loses_session_access(self):
        code = issue_access_code(self.event, self.worker)

        verify_conference_caller(
            "call-6", self.phone, code
        )

        EventMembership.objects.filter(
            event=self.event,
            user=self.worker,
        ).delete()

        self.assertIsNone(
            get_verified_conference(
                "call-6", self.phone
            )
        )

    def test_ended_conference_invalidates_session(self):
        code = issue_access_code(self.event, self.worker)

        verify_conference_caller(
            "call-7", self.phone, code
        )

        end_conference(
            self.event, self.organizer
        )

        self.assertIsNone(
            get_verified_conference(
                "call-7", self.phone
            )
        )

    def test_cleared_session_cannot_rejoin(self):
        code = issue_access_code(self.event, self.worker)

        verify_conference_caller(
            "call-8", self.phone, code
        )

        clear_verified_conference("call-8")

        self.assertIsNone(
            get_verified_conference(
                "call-8", self.phone
            )
        )

    def test_missing_session_id_is_rejected(self):
        code = issue_access_code(self.event, self.worker)

        with self.assertRaises(ValueError):
            verify_conference_caller(
                "", self.phone, code
            )
