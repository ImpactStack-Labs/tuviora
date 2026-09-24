from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import SMSPreference

from .models import Event, EventRegistration


User = get_user_model()


@override_settings(SMS_ENABLED=False)
class EventRegistrationAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="registration_organizer",
            password="TestPassword123!",
        )
        self.attendee = User.objects.create_user(
            username="registration_attendee",
            password="TestPassword123!",
        )
        self.other_attendee = User.objects.create_user(
            username="registration_other",
            password="TestPassword123!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Registration Test",
            category=Event.Category.HACKATHON,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            capacity=2,
            status=Event.Status.PUBLISHED,
        )

        self.registration_url = (
            f"/api/events/{self.event.id}/registrations/"
        )
        self.my_url = (
            f"/api/events/{self.event.id}/registrations/me/"
        )
        self.cancel_url = (
            f"/api/events/{self.event.id}/registrations/me/cancel/"
        )

        self.client.force_authenticate(user=self.attendee)

    def test_attendee_can_register(self):
        response = self.client.post(self.registration_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["user"], self.attendee.id)
        self.assertEqual(response.data["status"], "confirmed")

    def test_duplicate_registration_is_rejected(self):
        self.client.post(self.registration_url)
        response = self.client.post(self.registration_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            EventRegistration.objects.count(),
            1,
        )

    def test_attendee_can_view_own_registration(self):
        self.client.post(self.registration_url)

        response = self.client.get(self.my_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.attendee.id)

    def test_attendee_can_cancel_registration(self):
        self.client.post(self.registration_url)

        response = self.client.post(self.cancel_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "cancelled")

    def test_cancelled_attendee_can_register_again(self):
        self.client.post(self.registration_url)
        self.client.post(self.cancel_url)

        response = self.client.post(self.registration_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            EventRegistration.objects.count(),
            1,
        )
        self.assertEqual(response.data["status"], "confirmed")

    def test_capacity_is_enforced(self):
        self.event.capacity = 1
        self.event.save(update_fields=["capacity"])

        self.client.post(self.registration_url)

        self.client.force_authenticate(
            user=self.other_attendee
        )
        response = self.client.post(self.registration_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_draft_event_rejects_registration(self):
        self.event.status = Event.Status.DRAFT
        self.event.save(update_fields=["status"])

        response = self.client.post(self.registration_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_cancelled_event_rejects_registration(self):
        self.event.status = Event.Status.CANCELLED
        self.event.save(update_fields=["status"])

        response = self.client.post(self.registration_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_past_event_rejects_registration(self):
        self.event.date = timezone.localdate() - timedelta(
            days=1
        )
        self.event.save(update_fields=["date"])

        response = self.client.post(self.registration_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_only_organizer_can_list_attendees(self):
        self.client.post(self.registration_url)

        attendee_response = self.client.get(
            self.registration_url
        )
        self.assertEqual(
            attendee_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.client.force_authenticate(user=self.organizer)
        organizer_response = self.client.get(
            self.registration_url
        )

        self.assertEqual(
            organizer_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(organizer_response.data), 1)

    def test_other_user_cannot_view_my_registration(self):
        self.client.post(self.registration_url)

        self.client.force_authenticate(
            user=self.other_attendee
        )
        response = self.client.get(self.my_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_registration_is_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.registration_url)

        self.assertIn(response.status_code, [401, 403])
        self.assertEqual(
            EventRegistration.objects.count(),
            0,
        )

    def test_registration_does_not_enable_sms_consent(self):
        self.client.post(self.registration_url)

        self.assertFalse(
            SMSPreference.objects.filter(
                user=self.attendee,
                sms_enabled=True,
            ).exists()
        )
