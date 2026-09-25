from datetime import date, time, timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class FeedbackDedupeMigrationTests(TransactionTestCase):
    """0015 keeps the newest feedback per (event, attendee) before adding the constraint."""

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([("events", target)])
        return executor.loader.project_state([("events", target)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_keeps_newest_feedback_per_attendee(self):
        apps = self.migrate("0014_feedback_comment_blank")
        User = apps.get_model("auth", "User")
        Event = apps.get_model("events", "Event")
        Feedback = apps.get_model("events", "Feedback")
        a = User.objects.create(username="a")
        b = User.objects.create(username="b")
        event = Event.objects.create(
            organizer=a, name="E", category="conference", date=date(2026, 9, 26),
            start_time=time(9), end_time=time(10), status="published",
        )
        # Same updated_at: the higher id wins.
        a_old = Feedback.objects.create(event=event, attendee=a, rating=1)
        a_new = Feedback.objects.create(event=event, attendee=a, rating=5)
        Feedback.objects.filter(pk=a_old.pk).update(updated_at=a_new.updated_at)
        # Newer updated_at wins over a higher id.
        b_edited = Feedback.objects.create(event=event, attendee=b, rating=2)
        b_later = Feedback.objects.create(event=event, attendee=b, rating=3)
        Feedback.objects.filter(pk=b_edited.pk).update(
            updated_at=b_later.updated_at + timedelta(minutes=1)
        )
        anonymous = [Feedback.objects.create(event=event, rating=4) for _ in range(2)]

        apps = self.migrate("0015_feedback_unique_attendee")
        self.assertEqual(
            set(apps.get_model("events", "Feedback").objects.values_list("pk", flat=True)),
            {a_new.pk, b_edited.pk, *(f.pk for f in anonymous)},
        )
