from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventMembership


User = get_user_model()


class UserEventRoleTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="roles-organizer",
            email="organizer@example.com",
            password="test-password",
        )

        self.teammate = User.objects.create_user(
            username="roles-teammate",
            email="teammate@example.com",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Events Hackathon",
            category="hackathon",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        EventMembership.objects.create(
            event=self.event,
            user=self.teammate,
            role=EventMembership.Role.MEMBER,
        )

    def test_organizer_receives_organized_events(self):
        self.client.force_login(self.organizer)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["user"]["is_organizer"])
        self.assertEqual(
            response.json()["user"]["organized_events"][0]["id"],
            self.event.pk,
        )

    def test_teammate_receives_membership(self):
        self.client.force_login(self.teammate)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = response.json()["user"]

        self.assertFalse(user["is_organizer"])
        self.assertEqual(len(user["team_memberships"]), 1)
        self.assertEqual(
            user["team_memberships"][0]["event_id"],
            self.event.pk,
        )
        self.assertEqual(
            user["team_memberships"][0]["role"],
            "member",
        )

    def test_user_does_not_receive_other_peoples_events(self):
        outsider = User.objects.create_user(
            username="roles-outsider",
            password="test-password",
        )

        self.client.force_login(outsider)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["user"]["is_organizer"])
        self.assertEqual(response.json()["user"]["organized_events"], [])
        self.assertEqual(response.json()["user"]["team_memberships"], [])

    def test_unauthenticated_user_cannot_view_roles(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
