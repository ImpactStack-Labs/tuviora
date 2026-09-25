from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventMembership, Incident


User = get_user_model()


class TeamIncidentPermissionTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="incident-organizer",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="incident-manager",
            password="test-password",
        )
        self.member = User.objects.create_user(
            username="incident-member",
            password="test-password",
        )
        self.outsider = User.objects.create_user(
            username="incident-outsider",
            password="test-password",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Incident Test Event",
            category="hackathon",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        EventMembership.objects.create(
            event=self.event,
            user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.event,
            user=self.member,
            role=EventMembership.Role.MEMBER,
        )

        self.list_url = f"/api/events/{self.event.pk}/incidents/"
        self.payload = {
            "title": "Registration desk needs assistance",
            "description": "The registration queue is growing.",
            "category": "attendance",
            "severity": "medium",
        }

    def create_incident(self):
        return Incident.objects.create(
            event=self.event,
            reported_by=self.member,
            **self.payload,
        )

    def test_member_can_report_incident(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            self.list_url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["reported_by"], self.member.pk)
        self.assertEqual(response.data["status"], Incident.Status.OPEN)

    def test_member_can_view_event_incidents(self):
        incident = self.create_incident()
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], incident.pk)

    def test_member_cannot_update_incident(self):
        incident = self.create_incident()
        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"{self.list_url}{incident.pk}/",
            {"status": Incident.Status.RESOLVED},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.OPEN)

    def test_manager_can_update_incident(self):
        incident = self.create_incident()
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            f"{self.list_url}{incident.pk}/",
            {"status": Incident.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        self.assertEqual(
            incident.status,
            Incident.Status.IN_PROGRESS,
        )

    def test_outsider_cannot_view_incidents(self):
        self.create_incident()
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_outsider_cannot_report_incident(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            self.list_url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(Incident.objects.count(), 0)

    def test_member_cannot_access_another_event(self):
        another_event = Event.objects.create(
            organizer=self.outsider,
            name="Private Event",
            category="conference",
            date=timezone.localdate() + timedelta(days=12),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="Kampala",
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.get(
            f"/api/events/{another_event.pk}/incidents/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
