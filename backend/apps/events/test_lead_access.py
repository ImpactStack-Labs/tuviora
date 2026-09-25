from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import AIFeedbackAnalysis, Event, EventMembership

User = get_user_model()


def make_event(organizer, name):
    return Event.objects.create(
        organizer=organizer,
        name=name,
        category=Event.Category.WORKSHOP,
        date=timezone.localdate(),
        start_time="09:00",
        end_time="17:00",
        event_format=Event.EventFormat.PHYSICAL,
        venue="Kampala",
    )


class LeadEventAccessTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lead")
        other = User.objects.create_user(username="other")
        self.own = make_event(self.user, "Own")
        self.managed = make_event(other, "Managed")
        self.member_only = make_event(other, "Member only")
        make_event(other, "Unrelated")
        EventMembership.objects.create(
            event=self.managed, user=self.user,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.member_only, user=self.user,
            role=EventMembership.Role.MEMBER,
        )
        self.client.force_authenticate(user=self.user)

    def names(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return sorted(event["name"] for event in response.data)

    def test_default_list_is_organized_events_only(self):
        self.assertEqual(self.names("/api/events/"), ["Own"])

    def test_lead_scope_adds_managed_events(self):
        self.assertEqual(
            self.names("/api/events/?scope=lead"), ["Managed", "Own"],
        )

    def test_manager_can_use_feedback_analysis(self):
        url = f"/api/events/{self.managed.id}/feedback/analysis/"

        # No feedback yet: POST answers without calling the AI.
        self.assertEqual(self.client.post(url).status_code, 200)

        AIFeedbackAnalysis.objects.update_or_create(
            event=self.managed, defaults={"themes": []},
        )
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_member_and_outsider_cannot_use_feedback_analysis(self):
        url = f"/api/events/{self.member_only.id}/feedback/analysis/"
        self.assertEqual(self.client.get(url).status_code, 403)

        outsider = User.objects.create_user(username="outsider")
        self.client.force_authenticate(user=outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
