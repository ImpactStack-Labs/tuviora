"""Tests for private event conference management."""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.events.models import Event, EventMembership

from .conference_service import (
    ConferencePermissionError,
    ConferenceStateError,
    end_conference,
    start_conference,
)
from .models import EventConference


class ConferenceServiceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="service_organizer",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="service_manager",
            password="test-password",
        )
        self.worker = User.objects.create_user(
            username="service_worker",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="service_outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Conference Service Test",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        EventMembership.objects.create(
            event=self.event,
            user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.event,
            user=self.worker,
            role=EventMembership.Role.MEMBER,
        )

    def test_organizer_can_start_conference(self):
        conference = start_conference(
            self.event,
            self.organizer,
        )

        self.assertEqual(
            conference.status,
            EventConference.Status.ACTIVE,
        )
        self.assertEqual(
            conference.organizer,
            self.organizer,
        )
        self.assertIsNotNone(conference.started_at)
        self.assertTrue(
            conference.room_name.startswith("tuviora_")
        )

    def test_repeated_start_uses_same_conference(self):
        first = start_conference(
            self.event,
            self.organizer,
        )
        second = start_conference(
            self.event,
            self.organizer,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            first.room_name,
            second.room_name,
        )
        self.assertEqual(
            EventConference.objects.filter(
                event=self.event
            ).count(),
            1,
        )

    def test_manager_cannot_start_conference(self):
        with self.assertRaises(ConferencePermissionError):
            start_conference(
                self.event,
                self.manager,
            )

    def test_worker_cannot_start_conference(self):
        with self.assertRaises(ConferencePermissionError):
            start_conference(
                self.event,
                self.worker,
            )

    def test_outsider_cannot_start_conference(self):
        with self.assertRaises(ConferencePermissionError):
            start_conference(
                self.event,
                self.outsider,
            )

    def test_organizer_can_end_conference(self):
        start_conference(
            self.event,
            self.organizer,
        )

        conference = end_conference(
            self.event,
            self.organizer,
        )

        self.assertEqual(
            conference.status,
            EventConference.Status.ENDED,
        )
        self.assertIsNotNone(conference.ended_at)

    def test_worker_cannot_end_conference(self):
        start_conference(
            self.event,
            self.organizer,
        )

        with self.assertRaises(ConferencePermissionError):
            end_conference(
                self.event,
                self.worker,
            )

    def test_cannot_end_nonexistent_conference(self):
        with self.assertRaises(ConferenceStateError):
            end_conference(
                self.event,
                self.organizer,
            )

    def test_cannot_end_conference_twice(self):
        start_conference(
            self.event,
            self.organizer,
        )
        end_conference(
            self.event,
            self.organizer,
        )

        with self.assertRaises(ConferenceStateError):
            end_conference(
                self.event,
                self.organizer,
            )

    def test_cannot_restart_ended_conference(self):
        start_conference(
            self.event,
            self.organizer,
        )
        end_conference(
            self.event,
            self.organizer,
        )

        with self.assertRaises(ConferenceStateError):
            start_conference(
                self.event,
                self.organizer,
            )
