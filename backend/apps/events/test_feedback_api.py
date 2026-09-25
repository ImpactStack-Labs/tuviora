from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Event, EventMembership, EventRegistration, Feedback

User = get_user_model()


class FeedbackPermissionTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="org")
        self.manager = User.objects.create_user(username="mgr")
        self.member = User.objects.create_user(username="mem")
        self.attendee = User.objects.create_user(username="att")
        self.pending = User.objects.create_user(username="pend")
        self.outsider = User.objects.create_user(username="out")
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Feedback Event",
            category=Event.Category.WORKSHOP,
            date=timezone.localdate(),
            start_time="09:00",
            end_time="17:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        EventMembership.objects.create(
            event=self.event, user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.event, user=self.member,
            role=EventMembership.Role.MEMBER,
        )
        EventRegistration.objects.create(
            event=self.event, user=self.attendee,
            status=EventRegistration.Status.CONFIRMED,
        )
        EventRegistration.objects.create(
            event=self.event, user=self.pending,
            status=EventRegistration.Status.PAYMENT_PENDING,
        )
        self.url = f"/api/events/{self.event.id}/feedback/"

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def test_confirmed_attendee_submits_then_updates(self):
        self.as_user(self.attendee)

        first = self.client.post(self.url, {"rating": 4, "comment": "Good"}, format="json")
        second = self.client.post(self.url, {"rating": 5}, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        feedback = Feedback.objects.get()
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.comment, "")

    def test_unconfirmed_users_cannot_submit(self):
        for user in (self.pending, self.outsider):
            self.as_user(user)
            response = self.client.post(self.url, {"rating": 3}, format="json")
            self.assertEqual(response.status_code, 403)
        self.assertFalse(Feedback.objects.exists())

    def test_rating_or_comment_required(self):
        self.as_user(self.attendee)
        response = self.client.post(self.url, {"comment": "  "}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_list_restricted_to_organizer_and_managers(self):
        Feedback.objects.create(event=self.event, attendee=self.attendee, rating=4)
        expected = {
            self.organizer: 200,
            self.manager: 200,
            self.member: 403,
            self.attendee: 404,
            self.outsider: 404,
        }
        for user, code in expected.items():
            self.as_user(user)
            self.assertEqual(self.client.get(self.url).status_code, code, user.username)

    def test_my_feedback(self):
        self.as_user(self.attendee)
        me_url = f"{self.url}me/"
        self.assertEqual(self.client.get(me_url).status_code, 404)

        Feedback.objects.create(event=self.event, attendee=self.attendee, rating=2)

        response = self.client.get(me_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rating"], 2)
