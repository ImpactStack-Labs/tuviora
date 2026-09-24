"""Tests for private event conference authorization."""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.events.models import Event, EventMembership

from .conference import (
    can_join_conference,
    can_manage_conference,
    conference_role,
)


class ConferenceAuthorizationTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="conference_organizer",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="conference_manager",
            password="test-password",
        )
        self.worker = User.objects.create_user(
            username="conference_worker",
            password="test-password",
        )
        self.invitee = User.objects.create_user(
            username="conference_invitee",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="conference_outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Conference Test",
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

    def test_organizer_can_join_and_manage(self):
        self.assertEqual(
            conference_role(self.event, self.organizer),
            "organizer",
        )
        self.assertTrue(
            can_join_conference(self.event, self.organizer)
        )
        self.assertTrue(
            can_manage_conference(self.event, self.organizer)
        )

    def test_manager_can_join_but_not_manage(self):
        self.assertTrue(
            can_join_conference(self.event, self.manager)
        )
        self.assertFalse(
            can_manage_conference(self.event, self.manager)
        )

    def test_worker_can_join_but_not_manage(self):
        self.assertTrue(
            can_join_conference(self.event, self.worker)
        )
        self.assertFalse(
            can_manage_conference(self.event, self.worker)
        )

    def test_unaccepted_invitee_cannot_join(self):
        self.assertFalse(
            can_join_conference(self.event, self.invitee)
        )

    def test_outsider_cannot_join(self):
        self.assertFalse(
            can_join_conference(self.event, self.outsider)
        )

    def test_anonymous_user_cannot_join(self):
        self.assertFalse(
            can_join_conference(self.event, AnonymousUser())
        )

    def test_membership_is_event_specific(self):
        other_event = Event.objects.create(
            organizer=self.outsider,
            name="Another Event",
            category=Event.Category.WORKSHOP,
            date=date(2026, 9, 27),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        self.assertFalse(
            can_join_conference(other_event, self.worker)
        )
        self.assertFalse(
            can_join_conference(other_event, self.manager)
        )
