from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventMembership, ReadinessTask


User = get_user_model()


class TaskAssignmentTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="assignment-organizer",
            password="test-password",
        )
        self.member = User.objects.create_user(
            username="assignment-member",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="assignment-outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Assignment Test Event",
            category="hackathon",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        self.other_event = Event.objects.create(
            organizer=self.outsider,
            name="Other Assignment Event",
            category="workshop",
            date=timezone.localdate() + timedelta(days=12),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="Kampala",
        )

        EventMembership.objects.create(
            event=self.event,
            user=self.member,
            role=EventMembership.Role.MEMBER,
        )

        self.client.force_authenticate(user=self.organizer)

        self.deadline = (
            timezone.now() + timedelta(days=2)
        ).isoformat()

        self.url = f"/api/events/{self.event.pk}/tasks/"

    def create_task(self, assignee):
        return self.client.post(
            self.url,
            {
                "title": "Prepare event registration",
                "description": "Set up the registration desk.",
                "assignee": assignee,
                "deadline": self.deadline,
            },
            format="json",
        )

    def test_organizer_can_assign_accepted_member(self):
        response = self.create_task(self.member.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["assignee"],
            self.member.pk,
        )

    def test_organizer_can_assign_themselves(self):
        response = self.create_task(self.organizer.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_organizer_cannot_assign_outsider(self):
        response = self.create_task(self.outsider.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("assignee", response.data)

    def test_organizer_cannot_assign_member_of_another_event(self):
        EventMembership.objects.create(
            event=self.other_event,
            user=self.outsider,
            role=EventMembership.Role.MEMBER,
        )

        response = self.create_task(self.outsider.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("assignee", response.data)

    def test_organizer_can_reassign_to_accepted_member(self):
        task = ReadinessTask.objects.create(
            event=self.event,
            title="Confirm event equipment",
            assignee=self.organizer,
            deadline=timezone.now() + timedelta(days=2),
        )

        response = self.client.patch(
            f"{self.url}{task.pk}/",
            {"assignee": self.member.pk},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        task.refresh_from_db()
        self.assertEqual(task.assignee_id, self.member.pk)
