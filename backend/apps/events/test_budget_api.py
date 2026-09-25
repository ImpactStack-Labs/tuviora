from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import BudgetItem, Event, EventMembership

User = get_user_model()


class BudgetAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="org")
        self.manager = User.objects.create_user(username="mgr")
        self.member = User.objects.create_user(username="mem")
        self.outsider = User.objects.create_user(username="out")
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Budget Event",
            category=Event.Category.CONFERENCE,
            date=timezone.localdate(),
            start_time="09:00",
            end_time="17:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
        )
        EventMembership.objects.create(
            event=self.event, user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.event, user=self.member,
            role=EventMembership.Role.MEMBER,
        )
        self.url = f"/api/events/{self.event.id}/budget/"
        self.item = {
            "category": "catering",
            "description": "Lunch for 100",
            "vendor": "Kampala Caterers",
            "planned_amount": "1500000.00",
        }

    def test_manager_adds_updates_and_deletes_item(self):
        self.client.force_authenticate(user=self.manager)

        created = self.client.post(self.url, self.item, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["created_by"], self.manager.id)

        detail = f"{self.url}{created.data['id']}/"
        patched = self.client.patch(
            detail, {"actual_amount": "1400000.00", "paid": True}, format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertTrue(patched.data["paid"])

        self.assertEqual(self.client.get(self.url).data[0]["vendor"], "Kampala Caterers")
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(BudgetItem.objects.exists())

    def test_member_forbidden_outsider_not_found(self):
        self.client.force_authenticate(user=self.member)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(user=self.outsider)
        self.assertEqual(self.client.post(self.url, self.item, format="json").status_code, 404)

    def test_cannot_touch_another_events_item(self):
        other = Event.objects.create(
            organizer=self.outsider, name="Other",
            category=Event.Category.OTHER, date=timezone.localdate(),
            start_time="09:00", end_time="10:00",
            event_format=Event.EventFormat.PHYSICAL,
        )
        foreign = BudgetItem.objects.create(
            event=other, category="venue", description="Hall", planned_amount=1,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.patch(f"{self.url}{foreign.id}/", {"paid": True}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_negative_planned_amount_rejected(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            self.url, {**self.item, "planned_amount": "-1.00"}, format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_negative_actual_amount_rejected(self):
        self.client.force_authenticate(user=self.manager)
        created = self.client.post(self.url, self.item, format="json")
        detail = f"{self.url}{created.data['id']}/"
        response = self.client.patch(
            detail, {"actual_amount": "-5.00"}, format="json",
        )
        self.assertEqual(response.status_code, 400)
