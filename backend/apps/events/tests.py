from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, Incident, ReadinessTask


User = get_user_model()


class EventAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="organizer",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="other-organizer",
            password="test-password",
        )

        self.client.force_authenticate(user=self.user)

        self.event_data = {
            "name": "Tuviora Hackathon",
            "category": "hackathon",
            "description": "Technology event",
            "date": (timezone.localdate() + timedelta(days=10)).isoformat(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "event_format": "physical",
            "venue": "UCU Mukono",
            "landmark": "Main Campus",
            "latitude": "0.3944",
            "longitude": "32.5974",
            "capacity": 100,
        }

    def test_unauthenticated_user_cannot_access_events(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/events/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_create_event(self):
        response = self.client.post(
            "/api/events/",
            self.event_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Tuviora Hackathon")
        self.assertEqual(response.data["organizer"], self.user.id)
        self.assertEqual(response.data["status"], "draft")

    def test_event_organizer_comes_from_authenticated_user(self):
        response = self.client.post(
            "/api/events/",
            {
                **self.event_data,
                "organizer": self.other_user.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organizer"], self.user.id)

    def test_user_only_sees_own_events(self):
        Event.objects.create(
            organizer=self.other_user,
            name="Other Event",
            category="conference",
            date=timezone.localdate() + timedelta(days=5),
            start_time="09:00:00",
            end_time="12:00:00",
            venue="Other Venue",
        )

        own_event = Event.objects.create(
            organizer=self.user,
            name="My Event",
            category="conference",
            date=timezone.localdate() + timedelta(days=5),
            start_time="09:00:00",
            end_time="12:00:00",
            venue="My Venue",
        )

        response = self.client.get("/api/events/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own_event.id)


class ReadinessTaskAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="organizer",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="other-organizer",
            password="test-password",
        )

        self.client.force_authenticate(user=self.user)

        self.event = Event.objects.create(
            organizer=self.user,
            name="Tuviora Event",
            category="hackathon",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        self.other_event = Event.objects.create(
            organizer=self.other_user,
            name="Other Event",
            category="conference",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="Other Venue",
        )

        self.deadline = timezone.now() + timedelta(days=2)

        self.task_data = {
            "title": "Confirm venue equipment",
            "description": "Check microphones and projectors.",
            "assignee": self.user.id,
            "deadline": self.deadline.isoformat(),
        }

    def test_unauthenticated_user_cannot_access_tasks(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            f"/api/events/{self.event.id}/tasks/"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_can_create_readiness_task(self):
        response = self.client.post(
            f"/api/events/{self.event.id}/tasks/",
            self.task_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["event"], self.event.id)
        self.assertEqual(
            response.data["assignee"],
            self.user.id,
        )
        self.assertEqual(response.data["status"], "pending")

    def test_event_is_assigned_by_backend(self):
        response = self.client.post(
            f"/api/events/{self.event.id}/tasks/",
            {
                **self.task_data,
                "event": self.other_event.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["event"], self.event.id)

    def test_organizer_can_retrieve_tasks(self):
        task = ReadinessTask.objects.create(
            event=self.event,
            title="Test task",
            deadline=self.deadline,
        )

        response = self.client.get(
            f"/api/events/{self.event.id}/tasks/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], task.id)

    def test_organizer_can_update_task(self):
        task = ReadinessTask.objects.create(
            event=self.event,
            title="Test task",
            deadline=self.deadline,
        )

        response = self.client.patch(
            f"/api/events/{self.event.id}/tasks/{task.id}/",
            {
                "status": "in_progress",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "in_progress")

    def test_completing_task_sets_completed_at(self):
        task = ReadinessTask.objects.create(
            event=self.event,
            title="Test task",
            deadline=self.deadline,
        )

        response = self.client.patch(
            f"/api/events/{self.event.id}/tasks/{task.id}/",
            {
                "status": "completed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["completed_at"])

    def test_task_with_past_deadline_is_rejected(self):
        response = self.client.post(
            f"/api/events/{self.event.id}/tasks/",
            {
                **self.task_data,
                "deadline": (
                    timezone.now() - timedelta(days=1)
                ).isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("deadline", response.data)

    def test_user_cannot_access_tasks_for_another_organizers_event(self):
        response = self.client.get(
            f"/api/events/{self.other_event.id}/tasks/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class IncidentAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="organizer",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="other-organizer",
            password="test-password",
        )

        self.client.force_authenticate(user=self.user)

        self.event = Event.objects.create(
            organizer=self.user,
            name="Tuviora Event",
            category="hackathon",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        self.other_event = Event.objects.create(
            organizer=self.other_user,
            name="Other Event",
            category="conference",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="Other Venue",
        )

        self.incident_data = {
            "title": "Network connectivity problem",
            "description": "Internet connection is unstable.",
            "category": "network",
            "severity": "high",
        }

    def test_unauthenticated_user_cannot_access_incidents(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            f"/api/events/{self.event.id}/incidents/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_organizer_can_create_incident(self):
        response = self.client.post(
            f"/api/events/{self.event.id}/incidents/",
            self.incident_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["event"], self.event.id)
        self.assertEqual(
            response.data["reported_by"],
            self.user.id,
        )
        self.assertEqual(response.data["severity"], "high")
        self.assertEqual(response.data["status"], "open")

    def test_reporter_is_assigned_by_backend(self):
        response = self.client.post(
            f"/api/events/{self.event.id}/incidents/",
            {
                **self.incident_data,
                "reported_by": self.other_user.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["reported_by"],
            self.user.id,
        )

    def test_organizer_can_retrieve_incidents(self):
        incident = Incident.objects.create(
            event=self.event,
            title="Power outage",
            description="Venue power is unavailable.",
            category="power",
        )

        response = self.client.get(
            f"/api/events/{self.event.id}/incidents/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], incident.id)

    def test_organizer_can_update_incident(self):
        incident = Incident.objects.create(
            event=self.event,
            title="Power outage",
            description="Venue power is unavailable.",
            category="power",
        )

        response = self.client.patch(
            f"/api/events/{self.event.id}/incidents/{incident.id}/",
            {
                "status": "in_progress",
                "severity": "critical",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["status"],
            "in_progress",
        )
        self.assertEqual(
            response.data["severity"],
            "critical",
        )

    def test_resolving_incident_sets_resolved_at(self):
        incident = Incident.objects.create(
            event=self.event,
            title="Power outage",
            description="Venue power is unavailable.",
            category="power",
        )

        response = self.client.patch(
            f"/api/events/{self.event.id}/incidents/{incident.id}/",
            {
                "status": "resolved",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["resolved_at"])

    def test_invalid_incident_category_is_rejected(self):
        response = self.client.post(
            f"/api/events/{self.event.id}/incidents/",
            {
                **self.incident_data,
                "category": "invalid-category",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("category", response.data)

    def test_invalid_incident_severity_is_rejected(self):
        response = self.client.post(
            f"/api/events/{self.event.id}/incidents/",
            {
                **self.incident_data,
                "severity": "extreme",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("severity", response.data)

    def test_user_cannot_access_incidents_for_another_organizers_event(
        self,
    ):
        response = self.client.get(
            f"/api/events/{self.other_event.id}/incidents/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class AIIncidentAnalysisAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ai-organizer",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="other-ai-organizer",
            password="test-password",
        )

        self.client.force_authenticate(user=self.user)

        self.event = Event.objects.create(
            organizer=self.user,
            name="AI Test Event",
            category="conference",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="UCU Mukono",
        )

        self.other_event = Event.objects.create(
            organizer=self.other_user,
            name="Other AI Test Event",
            category="conference",
            date=timezone.localdate() + timedelta(days=10),
            start_time="09:00:00",
            end_time="17:00:00",
            venue="Other Venue",
        )

        self.incident = Incident.objects.create(
            event=self.event,
            title="Internet connection failure",
            description=(
                "The main event venue has lost its internet connection."
            ),
            category=Incident.Category.NETWORK,
            severity=Incident.Severity.MEDIUM,
            reported_by=self.user,
        )

        self.other_incident = Incident.objects.create(
            event=self.other_event,
            title="Power outage",
            description="The other venue has lost power.",
            category=Incident.Category.POWER,
            severity=Incident.Severity.HIGH,
            reported_by=self.other_user,
        )

        self.ai_result = {
            "classification": "network connectivity outage",
            "suggested_severity": "high",
            "priority": "urgent",
            "recommended_actions": [
                "Contact the network provider.",
                "Check the venue network equipment.",
                "Prepare an attendee communication.",
            ],
            "draft_message": (
                "We are currently experiencing a network issue at the venue. "
                "Our team is working to resolve it."
            ),
        }

    def test_ai_analysis_successfully_creates_recommendation(self):
        with self.mock_analyze_incident() as mock_analysis:
            mock_analysis.return_value = self.ai_result

            response = self.client.post(
                f"/api/events/incidents/{self.incident.id}/ai-analysis/",
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["classification"],
            "network connectivity outage",
        )
        self.assertEqual(
            response.data["suggested_severity"],
            "high",
        )
        self.assertEqual(
            response.data["priority"],
            "urgent",
        )
        self.assertEqual(
            response.data["approval_status"],
            "pending",
        )
        self.assertEqual(
            response.data["analysis_type"],
            "AI recommendation — not a verified fact",
        )
        self.assertEqual(
            response.data["draft_message"],
            self.ai_result["draft_message"],
        )

    def test_ai_service_failure_is_handled_gracefully(self):
        from unittest.mock import patch

        from .services.ai_incident_analysis import AIServiceError

        with patch(
            "apps.events.ai_views.analyze_incident",
            side_effect=AIServiceError("AI service unavailable"),
        ):
            response = self.client.post(
                f"/api/events/incidents/{self.incident.id}/ai-analysis/",
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertEqual(
            response.data["detail"],
            "AI incident analysis is currently unavailable.",
        )

    def test_organizer_can_retrieve_ai_analysis(self):
        from .models import AIIncidentAnalysis

        analysis = AIIncidentAnalysis.objects.create(
            incident=self.incident,
            classification="network connectivity outage",
            suggested_severity="high",
            priority="urgent",
            recommended_actions=[
                "Contact the network provider.",
            ],
            draft_message="We are experiencing a network issue.",
        )

        response = self.client.get(
            f"/api/events/incidents/{self.incident.id}/ai-analysis/detail/",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], analysis.id)
        self.assertEqual(response.data["incident_id"], self.incident.id)

    def test_organizer_can_approve_ai_recommendation(self):
        from .models import AIIncidentAnalysis

        analysis = AIIncidentAnalysis.objects.create(
            incident=self.incident,
            classification="network connectivity outage",
            suggested_severity="high",
            priority="urgent",
            recommended_actions=[
                "Contact the network provider.",
            ],
            draft_message="We are experiencing a network issue.",
        )

        response = self.client.post(
            f"/api/events/incidents/{self.incident.id}/ai-analysis/approve/",
            format="json",
        )

        analysis.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            analysis.approval_status,
            AIIncidentAnalysis.ApprovalStatus.APPROVED,
        )
        self.assertEqual(analysis.approved_by, self.user)
        self.assertIsNotNone(analysis.approved_at)

    def test_user_cannot_access_another_organizers_ai_analysis(self):
        response = self.client.post(
            f"/api/events/incidents/{self.other_incident.id}/ai-analysis/",
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_user_cannot_request_ai_analysis(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            f"/api/events/incidents/{self.incident.id}/ai-analysis/",
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def mock_analyze_incident(self):
        from unittest.mock import patch

        return patch(
            "apps.events.ai_views.analyze_incident"
        )
