from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventMembership, ReadinessTask


User = get_user_model()


class TeamTaskPermissionTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="task-organizer",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="task-manager",
            password="test-password",
        )
        self.member = User.objects.create_user(
            username="task-member",
            password="test-password",
        )
        self.other_member = User.objects.create_user(
            username="other-task-member",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="task-outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Team Task Test Event",
            category="hackathon",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        for user, role in (
            (self.manager, EventMembership.Role.MANAGER),
            (self.member, EventMembership.Role.MEMBER),
            (self.other_member, EventMembership.Role.MEMBER),
        ):
            EventMembership.objects.create(
                event=self.event,
                user=user,
                role=role,
            )

        self.deadline = timezone.now() + timedelta(days=2)

        self.my_task = ReadinessTask.objects.create(
            event=self.event,
            title="Prepare registration desk",
            assignee=self.member,
            deadline=self.deadline,
        )

        self.other_task = ReadinessTask.objects.create(
            event=self.event,
            title="Test venue equipment",
            assignee=self.other_member,
            deadline=self.deadline,
        )

        self.list_url = f"/api/events/{self.event.pk}/tasks/"

    def detail_url(self, task):
        return f"{self.list_url}{task.pk}/"

    def test_manager_can_view_all_event_tasks(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_member_sees_only_assigned_tasks(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.my_task.pk)

    def test_member_cannot_read_another_members_task(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.detail_url(self.other_task))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_member_can_update_own_task_status(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            self.detail_url(self.my_task),
            {"status": "in_progress"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.my_task.refresh_from_db()
        self.assertEqual(self.my_task.status, "in_progress")

    def test_member_cannot_change_task_details(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            self.detail_url(self.my_task),
            {"title": "Changed without permission"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.my_task.refresh_from_db()
        self.assertEqual(
            self.my_task.title,
            "Prepare registration desk",
        )

    def test_member_cannot_create_tasks(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            self.list_url,
            {
                "title": "Unauthorized task",
                "deadline": self.deadline.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_manager_can_update_task_status(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            self.detail_url(self.my_task),
            {"status": "in_progress"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_cannot_reassign_task(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            self.detail_url(self.my_task),
            {"assignee": self.manager.pk},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_outsider_cannot_list_event_tasks(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_outsider_cannot_read_event_task(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.detail_url(self.my_task))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
