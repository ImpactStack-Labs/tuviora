from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Event, EventRegistration


User = get_user_model()


class RegistrationConcurrencyTests(TransactionTestCase):
    def test_two_attendees_compete_for_one_place(self):
        organizer = User.objects.create_user(
            username="concurrency_organizer",
            password="TestPassword123!",
        )
        attendees = [
            User.objects.create_user(
                username=f"concurrency_attendee_{index}",
                password="TestPassword123!",
            )
            for index in range(2)
        ]

        event = Event.objects.create(
            organizer=organizer,
            name="One Remaining Place",
            category=Event.Category.HACKATHON,
            date=timezone.localdate() + timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            venue="Kampala",
            capacity=1,
            status=Event.Status.PUBLISHED,
        )

        barrier = Barrier(2)

        def register(attendee):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(user=attendee)
                barrier.wait(timeout=10)
                response = client.post(
                    f"/api/events/{event.pk}/registrations/"
                )
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(register, attendee)
                for attendee in attendees
            ]
            results = [future.result() for future in futures]

        confirmed = EventRegistration.objects.filter(
            event=event,
            status=EventRegistration.Status.CONFIRMED,
        ).count()

        self.assertEqual(
            confirmed,
            1,
            f"Capacity exceeded or no registration succeeded: {results}",
        )
        self.assertEqual(
            results.count(201),
            1,
            f"Expected exactly one successful registration: {results}",
        )
        self.assertTrue(
            all(code in (201, 409, 503) for code in results),
            f"Unexpected response codes: {results}",
        )
