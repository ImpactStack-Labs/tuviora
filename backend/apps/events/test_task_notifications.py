"""Tests for readiness task assignment email notifications."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventMembership, ReadinessTask


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Tuviora <test@example.com>",
    FRONTEND_BASE_URL="http://localhost:5173",
)
class TaskNotificationTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="notification-organizer",
            email="organizer@example.com",
            password="test-password",
        )

        self.member = User.objects.create_user(
            username="notification-member",
            email="member@example.com",
            password="test-password",
        )

        self.other_member = User.objects.create_user(
            username="notification-other",
            email="other@example.com",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Notification Test Event",
            category="hackathon",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        for member in (self.member, self.other_member):
            EventMembership.objects.create(
                event=self.event,
                user=member,
                role=EventMembership.Role.MEMBER,
            )

        self.client.force_authenticate(user=self.organizer)

        self.deadline = timezone.now() + timedelta(days=2)
        self.url = f"/api/events/{self.event.pk}/tasks/"

    def create_task(self, assignee):
        return self.client.post(
            self.url,
            {
                "title": "Prepare registration",
                "description": "Set up the registration desk.",
                "assignee": assignee,
                "deadline": self.deadline.isoformat(),
            },
            format="json",
        )

    def detail_url(self, task):
        return f"{self.url}{task.pk}/"

    def existing_task(self, assignee=None):
        return ReadinessTask.objects.create(
            event=self.event,
            title="Prepare registration",
            description="Set up the registration desk.",
            assignee=assignee,
            deadline=self.deadline,
        )

    def test_new_assignment_sends_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.create_task(self.member.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["member@example.com"],
        )
        self.assertIn(
            "Notification Test Event",
            mail.outbox[0].body,
        )
        self.assertIn(
            "Prepare registration",
            mail.outbox[0].body,
        )
        self.assertIn(
            "\n\n",
            mail.outbox[0].body,
        )
        self.assertIn(
            "http://localhost:5173/operations",
            mail.outbox[0].body,
        )

    def test_reassignment_emails_new_assignee_only(self):
        task = self.existing_task(self.member)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                self.detail_url(task),
                {"assignee": self.other_member.pk},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["other@example.com"],
        )

    def test_unchanged_assignment_sends_no_email(self):
        task = self.existing_task(self.member)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                self.detail_url(task),
                {"assignee": self.member.pk},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_unassignment_sends_no_email(self):
        task = self.existing_task(self.member)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                self.detail_url(task),
                {"assignee": None},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_status_change_sends_no_email(self):
        task = self.existing_task(self.member)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                self.detail_url(task),
                {"status": ReadinessTask.Status.IN_PROGRESS},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_does_not_undo_task_creation(self):
        with patch(
            "apps.events.task_notifications.send_mail",
            side_effect=RuntimeError("Simulated email failure"),
        ):
            with self.assertLogs(
                "apps.events.task_notifications",
                level="ERROR",
            ):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.create_task(self.member.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            ReadinessTask.objects.filter(
                event=self.event,
                assignee=self.member,
                title="Prepare registration",
            ).exists()
        )
