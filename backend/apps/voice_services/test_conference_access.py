"""Tests for private conference access codes."""

from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event, EventMembership

from .conference_access import (
    ConferenceAccessError,
    hash_access_code,
    issue_access_code,
    redeem_access_code,
)
from .conference_service import start_conference, end_conference
from .models import ConferenceAccessCode


class ConferenceAccessTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="access_organizer",
            password="test-password",
        )
        self.worker = User.objects.create_user(
            username="access_worker",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="access_outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Access Code Test",
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

    def test_organizer_can_receive_code(self):
        code = issue_access_code(
            self.event,
            self.organizer,
        )

        self.assertEqual(len(code), 8)
        self.assertTrue(code.isascii() and code.isdigit())

    def test_worker_can_receive_code(self):
        code = issue_access_code(
            self.event,
            self.worker,
        )

        conference, user = redeem_access_code(code)

        self.assertEqual(conference, self.conference)
        self.assertEqual(user, self.worker)

    def test_outsider_cannot_receive_code(self):
        with self.assertRaises(ConferenceAccessError):
            issue_access_code(
                self.event,
                self.outsider,
            )

    def test_code_is_stored_as_hash(self):
        code = issue_access_code(
            self.event,
            self.organizer,
        )

        credential = ConferenceAccessCode.objects.get(
            conference=self.conference,
            user=self.organizer,
        )

        self.assertNotEqual(credential.code_hash, code)
        self.assertEqual(
            credential.code_hash,
            hash_access_code(code),
        )

    def test_code_can_only_be_used_once(self):
        code = issue_access_code(
            self.event,
            self.worker,
        )

        redeem_access_code(code)

        with self.assertRaises(ConferenceAccessError):
            redeem_access_code(code)

    def test_expired_code_is_rejected(self):
        code = issue_access_code(
            self.event,
            self.worker,
        )

        ConferenceAccessCode.objects.filter(
            code_hash=hash_access_code(code),
        ).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        with self.assertRaises(ConferenceAccessError):
            redeem_access_code(code)

    def test_new_code_revokes_previous_code(self):
        first = issue_access_code(
            self.event,
            self.worker,
        )

        second = issue_access_code(
            self.event,
            self.worker,
        )

        with self.assertRaises(ConferenceAccessError):
            redeem_access_code(first)

        conference, user = redeem_access_code(second)

        self.assertEqual(conference, self.conference)
        self.assertEqual(user, self.worker)

    def test_removed_worker_cannot_redeem_code(self):
        code = issue_access_code(
            self.event,
            self.worker,
        )

        EventMembership.objects.filter(
            event=self.event,
            user=self.worker,
        ).delete()

        with self.assertRaises(ConferenceAccessError):
            redeem_access_code(code)

    def test_ended_conference_rejects_code(self):
        code = issue_access_code(
            self.event,
            self.worker,
        )

        end_conference(
            self.event,
            self.organizer,
        )

        with self.assertRaises(ConferenceAccessError):
            redeem_access_code(code)

    def test_invalid_code_is_rejected(self):
        for code in ("123", "abcdefgh", "123456789", "１２３４５６７８"):
            with self.subTest(code=code):
                with self.assertRaises(ConferenceAccessError):
                    redeem_access_code(code)

    def test_code_collision_triggers_retry(self):
        existing = issue_access_code(
            self.event,
            self.organizer,
        )

        alternative = (int(existing) + 1) % 100_000_000

        with patch(
            "apps.voice_services.conference_access.secrets.randbelow",
            side_effect=[int(existing), alternative],
        ) as generator:
            new_code = issue_access_code(
                self.event,
                self.worker,
            )

        self.assertEqual(generator.call_count, 2)
        self.assertEqual(new_code, f"{alternative:08d}")
        self.assertNotEqual(new_code, existing)

        conference, user = redeem_access_code(existing)
        self.assertEqual(conference, self.conference)
        self.assertEqual(user, self.organizer)

        conference, user = redeem_access_code(new_code)
        self.assertEqual(conference, self.conference)
        self.assertEqual(user, self.worker)

    def test_five_collisions_return_controlled_error(self):
        existing = issue_access_code(
            self.event,
            self.organizer,
        )

        with patch(
            "apps.voice_services.conference_access.secrets.randbelow",
            return_value=int(existing),
        ) as generator:
            with self.assertRaises(ConferenceAccessError):
                issue_access_code(
                    self.event,
                    self.worker,
                )

        self.assertEqual(generator.call_count, 5)

        self.assertFalse(
            ConferenceAccessCode.objects.filter(
                conference=self.conference,
                user=self.worker,
            ).exists()
        )

        conference, user = redeem_access_code(existing)
        self.assertEqual(conference, self.conference)
        self.assertEqual(user, self.organizer)
