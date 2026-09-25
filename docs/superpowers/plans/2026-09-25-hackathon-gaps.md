# Hackathon Focus-Area Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SMS announcements and reminders, attendee feedback (web + USSD), Payments/Analytics/Budget dashboards, and USSD registration for free events, per `docs/superpowers/specs/2026-09-25-hackathon-gaps-design.md`.

**Architecture:** Each feature adds a small service function in `backend/apps/events/services/`, thin DRF views that reuse one shared permission helper, and a React page that uses a shared `EventPicker`. USSD reuses the same services as the web API, so the rules live in one place.

**Tech Stack:** Django 6 + DRF, Africa's Talking (via existing `apps.sms` services), React 19 + Vite + Tailwind 4, Recharts, lucide-react.

## Global Constraints

- Backend commands run from `backend/` with `../.venv/bin/python`; `backend/.env` must contain `DJANGO_DEBUG=True`.
- Run a single test module: `../.venv/bin/python manage.py test apps.events.test_announcements_api` (dotted module path).
- Frontend checks run from `frontend/`: `npm run lint` and `npm run build`.
- Roles: organizer = `Event.organizer`; manager/member = `EventMembership.role`. Role lookup: `apps.events.views.task_access_for_user(event, user)` → `"organizer" | "manager" | "member" | None`.
- A user with no connection to the event gets `404`; a connected user without the right role gets `403`.
- SMS only through `apps.sms.services.event_sms_notifications.send_attendee_sms(user_ids, message)` (returns `{"submitted", "failed", "skipped"}`) or `apps.sms.services.sms_service.send_sms(phone, message)`. Tests always mock these.
- Announcement messages are 1–480 characters.
- USSD menu numbering: 1 Event information, 2 Check registration, 3 Staff incident report, **4 Register for an event**, **5 Rate an event**, 0 Exit.
- Frontend styling copies `pages/EventTeam.jsx` classes (cards: `rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6`; primary button: `rounded-xl bg-[#58761B] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50`).
- Git: all commands prefix `PATH="/usr/bin:$PATH"` (local `/usr/local/bin/git` is broken). Commit on the `dev` branch.

---

## File Structure

**Backend (`backend/apps/events/`)**
- `permissions.py` (new): `lead_event_or_deny(event_id, user)` — organizer/manager gate shared by all new organizer endpoints.
- `models.py` (modify): add `EventAnnouncement`, `BudgetItem`; `Feedback.comment` becomes `blank=True`.
- `services/announcements.py` (new): `announce_to_attendees`, `reminder_message`.
- `services/feedback.py` (new): `submit_feedback`, `FeedbackNotAllowed`.
- `services/registration.py` (new): `register_for_event`, `RegistrationError`.
- `services/summary.py` (new): `event_currency`, `event_summary`.
- `announcement_views.py`, `finance_views.py` (new); `views.py`, `registration_views.py`, `serializers.py`, `urls.py` (modify).
- `management/commands/send_event_reminders.py` (new).
- Tests: `test_announcements_api.py`, `test_feedback_api.py`, `test_budget_api.py`, `test_summary_api.py` (new); `tests.py` (modify `FeedbackAPITests.setUp`).

**Backend (`backend/apps/ussd/`)**: `views.py` (options 4 and 5), `tests.py` (new test classes).

**Frontend (`frontend/src/`)**
- `components/EventPicker.jsx`, `components/FeedbackForm.jsx` (new).
- `lib/announcements.js`, `lib/feedback.js`, `lib/finance.js` (new).
- `pages/Communications.jsx`, `pages/FeedbackPage.jsx`, `pages/PaymentsPage.jsx`, `pages/AnalyticsPage.jsx`, `pages/BudgetPage.jsx` (new).
- `layouts/OrganizerLayout.jsx`, `components/organizer/navigation.js`, `pages/MyRegistrations.jsx` (modify).

---

### Task 1: SMS announcements backend + reminder command

**Files:**
- Create: `backend/apps/events/permissions.py`
- Create: `backend/apps/events/services/announcements.py`
- Create: `backend/apps/events/announcement_views.py`
- Create: `backend/apps/events/management/__init__.py`, `backend/apps/events/management/commands/__init__.py` (both empty)
- Create: `backend/apps/events/management/commands/send_event_reminders.py`
- Modify: `backend/apps/events/models.py` (append `EventAnnouncement`)
- Modify: `backend/apps/events/urls.py`
- Test: `backend/apps/events/test_announcements_api.py`

**Interfaces:**
- Produces: `lead_event_or_deny(event_id, user) -> Event` (raises `Http404` / `PermissionDenied`); `announce_to_attendees(event, message, sent_by=None) -> EventAnnouncement`; `reminder_message(event) -> str`; model `EventAnnouncement(event, sent_by, message, submitted, failed, skipped, created_at)` with `related_name="announcements"`.

- [ ] **Step 1: Write the failing tests**

`backend/apps/events/test_announcements_api.py`:

```python
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Event,
    EventAnnouncement,
    EventMembership,
    EventRegistration,
)

User = get_user_model()
SEND = "apps.events.services.announcements.send_attendee_sms"
COUNTS = {"submitted": 1, "failed": 0, "skipped": 0}


def make_event(organizer, days_ahead=7, name="Demo Event"):
    return Event.objects.create(
        organizer=organizer,
        name=name,
        category=Event.Category.CONFERENCE,
        date=timezone.localdate() + timedelta(days=days_ahead),
        start_time="09:00",
        end_time="17:00",
        event_format=Event.EventFormat.PHYSICAL,
        venue="Kampala",
        status=Event.Status.PUBLISHED,
    )


class AnnouncementAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="org")
        self.manager = User.objects.create_user(username="mgr")
        self.member = User.objects.create_user(username="mem")
        self.outsider = User.objects.create_user(username="out")
        self.confirmed = User.objects.create_user(username="conf")
        self.pending = User.objects.create_user(username="pend")
        self.cancelled = User.objects.create_user(username="canc")
        self.event = make_event(self.organizer)
        EventMembership.objects.create(
            event=self.event, user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        EventMembership.objects.create(
            event=self.event, user=self.member,
            role=EventMembership.Role.MEMBER,
        )
        for user, reg_status in (
            (self.confirmed, EventRegistration.Status.CONFIRMED),
            (self.pending, EventRegistration.Status.PAYMENT_PENDING),
            (self.cancelled, EventRegistration.Status.CANCELLED),
        ):
            EventRegistration.objects.create(
                event=self.event, user=user, status=reg_status,
            )
        self.url = f"/api/events/{self.event.id}/announcements/"

    def post(self, user, message="Doors open at 8am."):
        self.client.force_authenticate(user=user)
        return self.client.post(self.url, {"message": message}, format="json")

    @patch(SEND, return_value=COUNTS)
    def test_organizer_sends_to_confirmed_attendees_only(self, send):
        response = self.post(self.organizer)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send.assert_called_once_with([self.confirmed.id], "Doors open at 8am.")
        self.assertEqual(response.data["submitted"], 1)
        announcement = EventAnnouncement.objects.get()
        self.assertEqual(announcement.sent_by, self.organizer)

    @patch(SEND, return_value=COUNTS)
    def test_manager_can_send(self, send):
        self.assertEqual(self.post(self.manager).status_code, 201)

    @patch(SEND, return_value=COUNTS)
    def test_member_forbidden_and_outsider_not_found(self, send):
        self.assertEqual(self.post(self.member).status_code, 403)
        self.assertEqual(self.post(self.outsider).status_code, 404)
        send.assert_not_called()

    @patch(SEND, return_value=COUNTS)
    def test_rejects_empty_and_overlong_messages(self, send):
        self.assertEqual(self.post(self.organizer, "   ").status_code, 400)
        self.assertEqual(self.post(self.organizer, "x" * 481).status_code, 400)
        send.assert_not_called()

    def test_history_is_scoped_to_event(self):
        other = make_event(self.organizer, name="Other")
        EventAnnouncement.objects.create(event=self.event, message="mine")
        EventAnnouncement.objects.create(event=other, message="theirs")
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([a["message"] for a in response.data], ["mine"])


class ReminderCommandTests(APITestCase):
    @patch(SEND, return_value=COUNTS)
    def test_reminds_tomorrows_events_once(self, send):
        organizer = User.objects.create_user(username="org")
        attendee = User.objects.create_user(username="att")
        tomorrow = make_event(organizer, days_ahead=1, name="Tomorrow")
        make_event(organizer, days_ahead=2, name="Later")
        EventRegistration.objects.create(
            event=tomorrow, user=attendee,
            status=EventRegistration.Status.CONFIRMED,
        )

        call_command("send_event_reminders")
        call_command("send_event_reminders")

        send.assert_called_once()
        user_ids, message = send.call_args.args
        self.assertEqual(user_ids, [attendee.id])
        self.assertTrue(message.startswith("Reminder: Tomorrow is tomorrow"))
        reminder = EventAnnouncement.objects.get()
        self.assertIsNone(reminder.sent_by)
        self.assertEqual(reminder.event, tomorrow)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python manage.py test apps.events.test_announcements_api`
Expected: ERROR — `ImportError: cannot import name 'EventAnnouncement'`.

- [ ] **Step 3: Add the model**

Append to `backend/apps/events/models.py`:

```python
class EventAnnouncement(models.Model):
    """An SMS sent to an event's confirmed attendees."""

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    # Null means an automatic reminder from send_event_reminders.
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_announcements",
    )
    message = models.TextField()
    submitted = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Announcement for {self.event.name}"
```

Run: `../.venv/bin/python manage.py makemigrations events -n eventannouncement`
Expected: creates `0013_eventannouncement.py`.

- [ ] **Step 4: Add the permission helper**

`backend/apps/events/permissions.py`:

```python
"""Shared per-event permission checks."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from .models import Event, EventMembership
from .views import task_access_for_user

LEAD_ROLES = ("organizer", EventMembership.Role.MANAGER)


def lead_event_or_deny(event_id, user):
    """Return the event when user is its organizer or a manager.

    Outsiders get 404 so private events stay hidden; members get 403.
    """
    event = get_object_or_404(Event, pk=event_id)
    role = task_access_for_user(event, user)

    if role is None:
        raise Http404

    if role not in LEAD_ROLES:
        raise PermissionDenied(
            "Only the organizer or event managers can do this."
        )

    return event
```

- [ ] **Step 5: Add the service**

`backend/apps/events/services/announcements.py`:

```python
"""Organizer announcements and reminders to confirmed attendees."""

from apps.sms.services.event_sms_notifications import send_attendee_sms

from ..models import EventAnnouncement, EventRegistration


def reminder_message(event):
    return (
        f"Reminder: {event.name} is tomorrow, {event.date:%d %b} "
        f"at {event.start_time:%H:%M}, {event.venue or 'online'}."
    )


def announce_to_attendees(event, message, sent_by=None):
    """SMS every confirmed attendee (consent is enforced downstream)."""
    user_ids = list(
        EventRegistration.objects.filter(
            event=event,
            status=EventRegistration.Status.CONFIRMED,
        ).values_list("user_id", flat=True)
    )
    counts = send_attendee_sms(user_ids, message)
    return EventAnnouncement.objects.create(
        event=event,
        sent_by=sent_by,
        message=message,
        **counts,
    )
```

- [ ] **Step 6: Add the views and URL**

`backend/apps/events/announcement_views.py`:

```python
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EventAnnouncement
from .permissions import lead_event_or_deny
from .services.announcements import announce_to_attendees


class EventAnnouncementSerializer(serializers.ModelSerializer):
    message = serializers.CharField(max_length=480)
    sent_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EventAnnouncement
        fields = [
            "id",
            "message",
            "submitted",
            "failed",
            "skipped",
            "sent_by",
            "sent_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "submitted",
            "failed",
            "skipped",
            "sent_by",
            "created_at",
        ]

    def get_sent_by_name(self, obj):
        if obj.sent_by is None:
            return None
        return obj.sent_by.get_full_name() or obj.sent_by.username


class EventAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        announcements = event.announcements.select_related("sent_by")
        return Response(
            EventAnnouncementSerializer(announcements, many=True).data
        )

    def post(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        serializer = EventAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = announce_to_attendees(
            event,
            serializer.validated_data["message"],
            sent_by=request.user,
        )
        return Response(
            EventAnnouncementSerializer(announcement).data,
            status=status.HTTP_201_CREATED,
        )
```

In `backend/apps/events/urls.py` add the import at the top and the route inside `urlpatterns`:

```python
from .announcement_views import EventAnnouncementView
```

```python
    path(
        "<int:event_id>/announcements/",
        EventAnnouncementView.as_view(),
        name="event-announcements",
    ),
```

- [ ] **Step 7: Add the reminder command**

Create empty `backend/apps/events/management/__init__.py` and `backend/apps/events/management/commands/__init__.py`, then `backend/apps/events/management/commands/send_event_reminders.py`:

```python
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event
from apps.events.services.announcements import (
    announce_to_attendees,
    reminder_message,
)


class Command(BaseCommand):
    help = "SMS confirmed attendees of events happening tomorrow. Run daily."

    def handle(self, *args, **options):
        today = timezone.localdate()
        events = Event.objects.filter(
            status=Event.Status.PUBLISHED,
            date=today + timedelta(days=1),
        )

        for event in events:
            already_sent = event.announcements.filter(
                sent_by__isnull=True,
                created_at__date=today,
            ).exists()

            if already_sent:
                self.stdout.write(f"{event.name}: reminder already sent today")
                continue

            result = announce_to_attendees(event, reminder_message(event))
            self.stdout.write(
                f"{event.name}: {result.submitted} sent, "
                f"{result.failed} failed, {result.skipped} skipped"
            )
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `../.venv/bin/python manage.py test apps.events.test_announcements_api`
Expected: `Ran 6 tests ... OK`.

- [ ] **Step 9: Document and commit**

In `docs/api/README.md`, under `## Team`'s table end, add a new section before `## Readiness tasks`:

```markdown
## Announcements

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET, POST | `/api/events/<event_id>/announcements/` | organizer or manager | Announcement history, or SMS `{"message": "..."}` (1–480 chars) to confirmed, opted-in attendees |

`python manage.py send_event_reminders` texts confirmed attendees of events happening tomorrow; run it daily from cron. Running it twice on the same day sends once.
```

In `docs/sms-integration.md`, under `## Other SMS triggers`, add the bullet `- Organizer announcements (POST /api/events/<event_id>/announcements/) and the daily send_event_reminders command.`

```bash
PATH="/usr/bin:$PATH" git add backend/apps/events docs/api/README.md docs/sms-integration.md
PATH="/usr/bin:$PATH" git commit -m "feat(events): SMS announcements to attendees and daily reminder command"
```

---

### Task 2: Communications page

**Files:**
- Create: `frontend/src/components/EventPicker.jsx`
- Create: `frontend/src/lib/announcements.js`
- Create: `frontend/src/pages/Communications.jsx`
- Modify: `frontend/src/layouts/OrganizerLayout.jsx`

**Interfaces:**
- Consumes: `GET/POST /api/events/<id>/announcements/` (Task 1).
- Produces: `<EventPicker id value onChange onError />` where `value` is the selected event object (or `null`) and `onChange(event)` receives the full event object; it auto-selects the first event. `OrganizerLayout` gains a `builtPaths` set used by later tasks.

- [ ] **Step 1: Shared event picker**

`frontend/src/components/EventPicker.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { getEvents, formatApiError } from '../lib/events'

export default function EventPicker({ id, value, onChange, onError }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    getEvents()
      .then((data) => {
        if (!active) return
        const list = Array.isArray(data) ? data : data.results || []
        setEvents(list)
        if (list.length) onChange(list[0])
      })
      .catch((err) => {
        if (active) onError?.(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
    // Load once; parents pass inline callbacks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        Select an event
      </label>
      <select
        id={id}
        value={value ? String(value.id) : ''}
        onChange={(e) =>
          onChange(events.find((ev) => String(ev.id) === e.target.value))
        }
        disabled={loading || !events.length}
        className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 outline-none focus:border-[#58761B] sm:max-w-xl"
      >
        {!events.length && (
          <option value="">{loading ? 'Loading events…' : 'No events available'}</option>
        )}
        {events.map((ev) => (
          <option key={ev.id} value={String(ev.id)}>
            {ev.name}
          </option>
        ))}
      </select>
      {value && (
        <p className="mt-3 text-sm text-text-muted">
          {value.category} · {value.date}
        </p>
      )}
    </section>
  )
}
```

- [ ] **Step 2: API helpers**

`frontend/src/lib/announcements.js`:

```js
import { apiRequest } from './auth'

export function getAnnouncements(eventId) {
  return apiRequest(`/api/events/${eventId}/announcements/`)
}

export function sendAnnouncement(eventId, message) {
  return apiRequest(`/api/events/${eventId}/announcements/`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}
```

- [ ] **Step 3: The page**

`frontend/src/pages/Communications.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { BellRing, Send } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import LoadingRow from '../components/LoadingRow'
import { getAnnouncements, sendAnnouncement } from '../lib/announcements'
import { formatApiError } from '../lib/events'
import { formatDateTime, formatEventDate } from '../lib/format'

const MAX_LENGTH = 480

function smsSegments(text) {
  if (!text.length) return 0
  return text.length <= 160 ? 1 : Math.ceil(text.length / 153)
}

function reminderTemplate(event) {
  return (
    `Reminder: ${event.name} is on ${formatEventDate(event.date)} ` +
    `at ${String(event.start_time).slice(0, 5)}, ${event.venue || 'online'}.`
  )
}

export default function Communications() {
  const [event, setEvent] = useState(null)
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!event) return
    let active = true
    setLoading(true)

    getAnnouncements(event.id)
      .then((data) => { if (active) setAnnouncements(data) })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event, refreshKey])

  async function handleSend(e) {
    e.preventDefault()
    if (!event || sending || !message.trim()) return
    if (!window.confirm('Send this SMS to all confirmed attendees?')) return

    setSending(true)
    setError('')
    setNotice('')

    try {
      const result = await sendAnnouncement(event.id, message.trim())
      setMessage('')
      setNotice(
        `Sent to ${result.submitted} · ${result.skipped} skipped ` +
        `(no SMS consent or phone) · ${result.failed} failed.`,
      )
      setRefreshKey((k) => k + 1)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Attendee communication
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Communications
        </h1>
        <p className="mt-3 max-w-2xl text-text-muted">
          Send SMS announcements and reminders to confirmed attendees who
          opted in to SMS.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}
      {notice && (
        <div role="status" className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          {notice}
        </div>
      )}

      <EventPicker
        id="communications-event"
        value={event}
        onChange={(ev) => { setEvent(ev); setNotice(''); setError('') }}
        onError={setError}
      />

      <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-[#1A3F22]">New announcement</h2>
          <button
            type="button"
            disabled={!event}
            onClick={() => setMessage(reminderTemplate(event))}
            className="inline-flex items-center gap-2 rounded-xl border border-border-soft bg-white px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            <BellRing size={16} /> Insert reminder
          </button>
        </div>
        <form onSubmit={handleSend} className="mt-4 space-y-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            maxLength={MAX_LENGTH}
            rows={4}
            aria-label="Announcement message"
            placeholder="e.g. Doors open at 8am. Bring your ticket QR code."
            className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 outline-none focus:border-[#58761B]"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-text-muted">
              {message.length}/{MAX_LENGTH} characters · {smsSegments(message)} SMS
            </p>
            <button
              type="submit"
              disabled={!event || sending || !message.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-[#58761B] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              <Send size={16} /> {sending ? 'Sending...' : 'Send to attendees'}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-xl font-bold">History</h2>
        {loading && <LoadingRow className="mt-4" />}
        {!loading && !announcements.length && (
          <p className="mt-4 text-sm text-text-muted">No announcements sent yet.</p>
        )}
        <ul className="mt-4 divide-y divide-[#EDF1EA]">
          {announcements.map((a) => (
            <li key={a.id} className="py-4">
              <p className="text-sm text-text-muted">
                {formatDateTime(a.created_at)} · {a.sent_by_name || 'Automatic reminder'}
              </p>
              <p className="mt-1">{a.message}</p>
              <p className="mt-1 text-sm text-text-muted">
                {a.submitted} sent · {a.skipped} skipped · {a.failed} failed
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
```

- [ ] **Step 4: Route it**

In `frontend/src/layouts/OrganizerLayout.jsx`:
1. Add `import Communications from '../pages/Communications'` after the `IncidentManagement` import.
2. Above `export default function OrganizerLayout`, add:

```jsx
// Sidebar paths that have a real page; the rest render the placeholder.
const builtPaths = new Set([
  'events', 'readiness', 'team', 'registration', 'attendance',
  'live', 'incidents', 'communications',
])
```

3. Add `<Route path="communications" element={<Communications />} />` after the `incidents` route.
4. Replace the long `.filter(({ path }) => path !== 'events' && ...)` with `.filter(({ path }) => !builtPaths.has(path))`.

- [ ] **Step 5: Verify**

Run from `frontend/`: `npm run lint && npm run build`
Expected: no lint errors; build succeeds.

Manual: open `http://localhost:5173/operations/communications` as an organizer, pick an event, click **Insert reminder**, send; the notice shows counts and the history lists the message.

- [ ] **Step 6: Commit**

```bash
PATH="/usr/bin:$PATH" git add frontend/src
PATH="/usr/bin:$PATH" git commit -m "feat(frontend): Communications page for SMS announcements"
```

---

### Task 3: Feedback API — permissions, upsert, `feedback/me/`

**Files:**
- Create: `backend/apps/events/services/feedback.py`
- Modify: `backend/apps/events/models.py` (`Feedback.comment`)
- Modify: `backend/apps/events/serializers.py` (`FeedbackSerializer.validate`)
- Modify: `backend/apps/events/views.py` (replace `FeedbackListCreateView`, add `MyFeedbackView`)
- Modify: `backend/apps/events/urls.py`
- Modify: `backend/apps/events/tests.py` (`FeedbackAPITests.setUp`)
- Test: `backend/apps/events/test_feedback_api.py`

**Interfaces:**
- Consumes: `lead_event_or_deny` (Task 1).
- Produces: `submit_feedback(event, user, rating=None, comment="") -> (Feedback, created: bool)`; raises `FeedbackNotAllowed` when the user has no confirmed registration.

- [ ] **Step 1: Write the failing tests**

`backend/apps/events/test_feedback_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python manage.py test apps.events.test_feedback_api`
Expected: FAIL — e.g. pending user gets `201` instead of `403`; `me/` returns `404` for the route itself on the second call.

- [ ] **Step 3: Allow blank comments**

In `backend/apps/events/models.py`, class `Feedback`, change `comment = models.TextField()` to:

```python
    comment = models.TextField(blank=True)
```

Run: `../.venv/bin/python manage.py makemigrations events -n feedback_comment_blank`
Expected: creates `0014_feedback_comment_blank.py`.

- [ ] **Step 4: Service**

`backend/apps/events/services/feedback.py`:

```python
"""Attendee feedback shared by the web API and USSD."""

from ..models import EventRegistration, Feedback


class FeedbackNotAllowed(Exception):
    """The user has no confirmed registration for the event."""


def submit_feedback(event, user, rating=None, comment=""):
    """Create or update the user's single feedback for this event."""
    is_confirmed = EventRegistration.objects.filter(
        event=event,
        user=user,
        status=EventRegistration.Status.CONFIRMED,
    ).exists()

    if not is_confirmed:
        raise FeedbackNotAllowed(
            "Only confirmed attendees can give feedback."
        )

    # ponytail: no DB unique constraint; two simultaneous first submissions
    # could duplicate. Add UniqueConstraint(event, attendee) if that shows up.
    return Feedback.objects.update_or_create(
        event=event,
        attendee=user,
        defaults={"rating": rating, "comment": comment},
    )
```

- [ ] **Step 5: Serializer validation**

In `backend/apps/events/serializers.py`, add this method inside `FeedbackSerializer` (after `class Meta`):

```python
    def validate(self, attrs):
        if attrs.get("rating") is None and not attrs.get("comment", "").strip():
            raise serializers.ValidationError(
                "Give a rating, a comment, or both."
            )
        return attrs
```

- [ ] **Step 6: Views and URL**

In `backend/apps/events/views.py`, replace the whole `class FeedbackListCreateView(generics.ListCreateAPIView): ...` block with:

```python
class FeedbackListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        from .permissions import lead_event_or_deny

        event = lead_event_or_deny(event_id, request.user)
        feedback = event.feedback.select_related("attendee")
        return Response(FeedbackSerializer(feedback, many=True).data)

    def post(self, request, event_id):
        from .services.feedback import FeedbackNotAllowed, submit_feedback

        event = get_object_or_404(Event, pk=event_id)
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            feedback, created = submit_feedback(
                event,
                request.user,
                rating=serializer.validated_data.get("rating"),
                comment=serializer.validated_data.get("comment", "").strip(),
            )
        except FeedbackNotAllowed as exc:
            raise PermissionDenied(str(exc))

        return Response(
            FeedbackSerializer(feedback).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        feedback = get_object_or_404(
            Feedback, event_id=event_id, attendee=request.user,
        )
        return Response(FeedbackSerializer(feedback).data)
```

(`permissions.py` imports from `views.py`, so the function-level imports avoid a circular import.) Confirm `views.py` already imports `APIView`, `Response`, `status`, `PermissionDenied`, `get_object_or_404`, `Feedback`, `Event`; add any that are missing to its existing import lines.

In `backend/apps/events/urls.py`, add `MyFeedbackView` to the `from .views import (...)` list and add:

```python
    path(
        "<int:event_id>/feedback/me/",
        MyFeedbackView.as_view(),
        name="my-event-feedback",
    ),
```

- [ ] **Step 7: Update the old feedback tests**

In `backend/apps/events/tests.py`, add `EventRegistration` to the `from .models import (...)` list, and at the end of `FeedbackAPITests.setUp` (before `self.client.force_authenticate(user=self.user)`) add:

```python
        # Submitting feedback now requires a confirmed registration.
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            status=EventRegistration.Status.CONFIRMED,
        )
```

- [ ] **Step 8: Run tests**

Run: `../.venv/bin/python manage.py test apps.events.test_feedback_api apps.events.tests`
Expected: all pass.

- [ ] **Step 9: Document and commit**

In `docs/api/README.md`, `## AI (OpenAI)` table, replace the feedback row with:

```markdown
| GET | `/api/events/<event_id>/feedback/` | organizer or manager | List attendee feedback |
| POST | `/api/events/<event_id>/feedback/` | confirmed attendee | Submit or update your feedback: `rating` (1–5) and/or `comment`. `201` created, `200` updated |
| GET | `/api/events/<event_id>/feedback/me/` | signed in | Your own feedback for the event (`404` if none) |
```

```bash
PATH="/usr/bin:$PATH" git add backend/apps/events docs/api/README.md
PATH="/usr/bin:$PATH" git commit -m "fix(feedback): only confirmed attendees submit, only leads read; one feedback per attendee"
```

---

### Task 4: USSD "5. Rate an event"

**Files:**
- Modify: `backend/apps/ussd/views.py`
- Test: `backend/apps/ussd/tests.py` (append class)

**Interfaces:**
- Consumes: `submit_feedback` (Task 3); `apps.voice_services.events.get_registration(event_id, phone)`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/ussd/tests.py`:

```python
from apps.events.models import Feedback


class USSDFeedbackTests(TestCase):
    def setUp(self):
        self.url = reverse("ussd-callback")
        self.phone = "+256712345678"
        organizer = get_user_model().objects.create_user(username="organizer")
        self.attendee = get_user_model().objects.create_user(username="attendee")
        SMSPreference.objects.create(
            user=self.attendee, phone_number=self.phone, sms_enabled=True,
        )
        self.event = Event.objects.create(
            organizer=organizer,
            name="Tuviora Summit",
            category=Event.Category.CONFERENCE,
            date=date(2026, 9, 26),
            start_time=time(9, 0),
            end_time=time(17, 0),
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        EventRegistration.objects.create(
            event=self.event, user=self.attendee,
            status=EventRegistration.Status.CONFIRMED,
        )

    def send(self, text, phone=None):
        return self.client.post(self.url, {
            "sessionId": "s1",
            "serviceCode": "*384*123#",
            "phoneNumber": phone or self.phone,
            "text": text,
        }).content.decode()

    def test_menu_lists_rating(self):
        self.assertIn("5. Rate an event", self.send(""))

    def test_rates_with_comment(self):
        e = self.event.pk
        self.assertIn("CON Enter the event ID", self.send("5"))
        self.assertIn("CON Rate Tuviora Summit", self.send(f"5*{e}"))
        self.assertIn("CON Add a comment", self.send(f"5*{e}*4"))
        self.assertEqual(
            self.send(f"5*{e}*4*Great talks*loved it"),
            "END Thank you for your feedback.",
        )
        feedback = Feedback.objects.get()
        self.assertEqual((feedback.rating, feedback.comment), (4, "Great talks*loved it"))

    def test_skip_comment_with_9(self):
        self.send(f"5*{self.event.pk}*5*9")
        self.assertEqual(Feedback.objects.get().comment, "")

    def test_invalid_rating(self):
        self.assertEqual(
            self.send(f"5*{self.event.pk}*7"),
            "END Invalid rating. Please dial again.",
        )

    def test_unknown_phone_gets_generic_reply(self):
        self.assertEqual(
            self.send(f"5*{self.event.pk}", phone="+256700000001"),
            "END No registration found for this event.",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python manage.py test apps.ussd`
Expected: the five new tests FAIL (menu has no option 5; `5` gives "Invalid choice").

- [ ] **Step 3: Implement**

In `backend/apps/ussd/views.py`:

1. Add imports:

```python
from apps.events.models import EventRegistration
from apps.events.services.feedback import submit_feedback
```

2. Replace `MAIN_MENU` with:

```python
MAIN_MENU = (
    "CON Welcome to Tuviora\n"
    "1. Event information\n"
    "2. Check registration\n"
    "3. Staff incident report\n"
    "5. Rate an event\n"
    "0. Exit"
)
```

3. Add this function above `ussd_callback`:

```python
def rate_event(parts, phone):
    """Option 5: rate a confirmed registration, then optionally comment."""
    if len(parts) == 1:
        return reply("CON", "Enter the event ID:")
    if not parts[1].isdigit():
        return reply("END", "Invalid event ID. Please dial again.")

    try:
        registration = get_registration(parts[1], phone)
    except Exception:
        return reply("END", "Feedback is unavailable. Please try later.")

    if (
        registration is None
        or registration.status != EventRegistration.Status.CONFIRMED
    ):
        return reply("END", "No registration found for this event.")

    if len(parts) == 2:
        return reply(
            "CON",
            f"Rate {registration.event.name} from 1 (poor) to 5 (excellent):",
        )
    if parts[2] not in {"1", "2", "3", "4", "5"}:
        return reply("END", "Invalid rating. Please dial again.")
    if len(parts) == 3:
        return reply("CON", "Add a comment, or enter 9 to skip:")

    # Africa's Talking joins inputs with "*", so rejoin a comment containing it.
    comment = "*".join(parts[3:]).strip()
    submit_feedback(
        registration.event,
        registration.user,
        rating=int(parts[2]),
        comment="" if comment == "9" else comment,
    )
    return reply("END", "Thank you for your feedback.")
```

4. In `ussd_callback`, before the final `return reply("CON", "Invalid choice...")`, add:

```python
    if parts[0] == "5":
        return rate_event(parts, phone)
```

- [ ] **Step 4: Run tests**

Run: `../.venv/bin/python manage.py test apps.ussd`
Expected: all pass (existing + 5 new).

- [ ] **Step 5: Document and commit**

In `docs/ussd-sandbox.md`, update the first bullet under `## Flows to check` to: `- The opening menu lists event information, registration check, staff reporting, rating, and exit.` and add:

```markdown
- Choose `5`, enter the ID of an event where the caller's phone has a confirmed
  registration, rate 1–5, then type a comment or `9` to skip. The feedback
  appears on the organizer's Feedback page. Callers without a confirmed
  registration get the same generic "No registration found for this event."
```

```bash
PATH="/usr/bin:$PATH" git add backend/apps/ussd docs/ussd-sandbox.md
PATH="/usr/bin:$PATH" git commit -m "feat(ussd): rate an event and leave a comment"
```

---

### Task 5: Feedback frontend (attendee form + organizer page)

**Files:**
- Create: `frontend/src/lib/feedback.js`
- Create: `frontend/src/components/FeedbackForm.jsx`
- Create: `frontend/src/pages/FeedbackPage.jsx`
- Modify: `frontend/src/pages/MyRegistrations.jsx`
- Modify: `frontend/src/layouts/OrganizerLayout.jsx`

**Interfaces:**
- Consumes: Task 3 endpoints; existing `GET/POST /api/events/<id>/feedback/analysis/` (GET `404` when none; POST `503` when OpenAI is unavailable). Analysis shape: `{themes: [{theme, description, frequency}], concerns_summary, suggested_improvements: [string], message?}`.

- [ ] **Step 1: API helpers**

`frontend/src/lib/feedback.js`:

```js
import { apiRequest } from './auth'

export function getEventFeedback(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/`)
}

export function getMyFeedback(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/me/`)
}

export function submitFeedback(eventId, { rating, comment }) {
  return apiRequest(`/api/events/${eventId}/feedback/`, {
    method: 'POST',
    body: JSON.stringify({ rating, comment }),
  })
}

export function getFeedbackAnalysis(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/analysis/`)
}

export function generateFeedbackAnalysis(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/analysis/`, {
    method: 'POST',
  })
}
```

- [ ] **Step 2: Attendee form**

`frontend/src/components/FeedbackForm.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { Star } from 'lucide-react'
import { getMyFeedback, submitFeedback } from '../lib/feedback'
import { formatApiError } from '../lib/events'

export default function FeedbackForm({ eventId }) {
  const [rating, setRating] = useState(null)
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    getMyFeedback(eventId)
      .then((data) => {
        if (!active) return
        setRating(data.rating)
        setComment(data.comment || '')
      })
      .catch(() => {}) // 404: no feedback yet
    return () => { active = false }
  }, [eventId])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      await submitFeedback(eventId, { rating, comment: comment.trim() })
      setMessage('Thanks — your feedback was saved.')
    } catch (err) {
      setMessage(formatApiError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 border-t border-border-soft pt-5">
      <p className="text-sm font-semibold">Rate this event</p>
      <div className="mt-2 flex gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={rating === value}
            aria-label={`${value} star${value > 1 ? 's' : ''}`}
            onClick={() => setRating(value)}
            className="rounded-lg p-1"
          >
            <Star
              size={24}
              className={rating >= value ? 'fill-[#58761B] text-[#58761B]' : 'text-[#B7C2B4]'}
            />
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
        aria-label="Feedback comment"
        placeholder="What went well? What could be better?"
        className="mt-3 w-full rounded-xl border border-border-soft px-4 py-3 text-sm outline-none focus:border-[#58761B]"
      />
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={saving || (rating === null && !comment.trim())}
          className="rounded-xl bg-[#58761B] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Submit feedback'}
        </button>
        {message && <p role="status" className="text-sm text-text-muted">{message}</p>}
      </div>
    </form>
  )
}
```

- [ ] **Step 3: Add the form to My Registrations**

In `frontend/src/pages/MyRegistrations.jsx`:
1. Add `import FeedbackForm from '../components/FeedbackForm'` after the `LoadingRow` import.
2. In `registrationCard`, immediately before the closing `</article>`, add:

```jsx
        {confirmed && <FeedbackForm eventId={item.event.id} />}
```

- [ ] **Step 4: Organizer page**

`frontend/src/pages/FeedbackPage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { MessageSquare, Sparkles, Star } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import StatCard from '../components/StatCard'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import { formatDateTime } from '../lib/format'
import {
  generateFeedbackAnalysis,
  getEventFeedback,
  getFeedbackAnalysis,
} from '../lib/feedback'

export default function FeedbackPage() {
  const [event, setEvent] = useState(null)
  const [feedback, setFeedback] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!event) return
    let active = true
    setLoading(true)
    setAnalysis(null)

    Promise.all([
      getEventFeedback(event.id),
      getFeedbackAnalysis(event.id).catch(() => null), // 404: none yet
    ])
      .then(([items, existing]) => {
        if (!active) return
        setFeedback(items)
        setAnalysis(existing)
      })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event])

  async function handleAnalyze() {
    setAnalyzing(true)
    setError('')
    try {
      setAnalysis(await generateFeedbackAnalysis(event.id))
    } catch (err) {
      setError(
        err.status === 503
          ? 'AI summary unavailable — OPENAI_API_KEY is not configured.'
          : formatApiError(err),
      )
    } finally {
      setAnalyzing(false)
    }
  }

  const rated = feedback.filter((f) => f.rating)
  const average = rated.length
    ? (rated.reduce((sum, f) => sum + f.rating, 0) / rated.length).toFixed(1)
    : '—'
  const breakdown = [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: rated.filter((f) => f.rating === star).length,
  }))

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Attendee voice
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Feedback
        </h1>
        <p className="mt-3 max-w-2xl text-text-muted">
          Ratings and comments from attendees on the web and USSD.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="feedback-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {event && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <StatCard label="Average rating" value={average} icon={Star} caption="out of 5" />
            <StatCard label="Responses" value={feedback.length} icon={MessageSquare} />
          </div>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold">Rating breakdown</h2>
            <div className="mt-4 space-y-2">
              {breakdown.map(({ star, count }) => (
                <div key={star} className="flex items-center gap-3 text-sm">
                  <span className="w-10">{star} ★</span>
                  <div className="h-2 flex-1 rounded-full bg-[#EDF1EA]">
                    <div
                      className="h-2 rounded-full bg-[#58761B]"
                      style={{ width: rated.length ? `${(count / rated.length) * 100}%` : 0 }}
                    />
                  </div>
                  <span className="w-8 text-right text-text-muted">{count}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">AI summary</h2>
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={analyzing || !feedback.length}
                className="inline-flex items-center gap-2 rounded-xl bg-[#58761B] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                <Sparkles size={16} /> {analyzing ? 'Analysing...' : 'Generate AI summary'}
              </button>
            </div>
            {!analysis && (
              <p className="mt-3 text-sm text-text-muted">No summary generated yet.</p>
            )}
            {analysis && (
              <div className="mt-4 space-y-4 text-sm">
                {analysis.message && <p className="text-text-muted">{analysis.message}</p>}
                {analysis.concerns_summary && <p>{analysis.concerns_summary}</p>}
                {analysis.themes?.length > 0 && (
                  <ul className="space-y-2">
                    {analysis.themes.map((t, i) => (
                      <li key={i}>
                        <span className="font-semibold">{t.theme ?? String(t)}</span>
                        {t.description && ` — ${t.description}`}
                      </li>
                    ))}
                  </ul>
                )}
                {analysis.suggested_improvements?.length > 0 && (
                  <div>
                    <p className="font-semibold">Suggested improvements</p>
                    <ul className="mt-1 list-disc pl-5">
                      {analysis.suggested_improvements.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold">Comments</h2>
            {!feedback.length && (
              <p className="mt-3 text-sm text-text-muted">No feedback yet.</p>
            )}
            <ul className="mt-3 divide-y divide-[#EDF1EA]">
              {feedback.map((f) => (
                <li key={f.id} className="py-3 text-sm">
                  <p className="text-text-muted">
                    {f.rating ? `${f.rating} ★ · ` : ''}{formatDateTime(f.created_at)}
                  </p>
                  {f.comment && <p className="mt-1">{f.comment}</p>}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Route it**

In `frontend/src/layouts/OrganizerLayout.jsx`: add `import FeedbackPage from '../pages/FeedbackPage'`, add `'feedback'` to `builtPaths`, and add `<Route path="feedback" element={<FeedbackPage />} />` after the `communications` route.

- [ ] **Step 6: Verify**

Run from `frontend/`: `npm run lint && npm run build`
Expected: clean.

Manual: as a confirmed attendee on `/my-registrations`, submit 4 stars + comment; as the organizer on `/operations/feedback`, the response and breakdown appear.

- [ ] **Step 7: Commit**

```bash
PATH="/usr/bin:$PATH" git add frontend/src
PATH="/usr/bin:$PATH" git commit -m "feat(frontend): attendee feedback form and organizer Feedback page"
```

---

### Task 6: Budget items API

**Files:**
- Create: `backend/apps/events/finance_views.py`
- Modify: `backend/apps/events/models.py` (append `BudgetItem`)
- Modify: `backend/apps/events/urls.py`
- Test: `backend/apps/events/test_budget_api.py`

**Interfaces:**
- Consumes: `lead_event_or_deny` (Task 1).
- Produces: model `BudgetItem` (`related_name="budget_items"`), `BudgetItemSerializer`, views `BudgetItemListCreateView`, `BudgetItemDetailView` in `finance_views.py` (Task 7 adds more views to this file).

- [ ] **Step 1: Write the failing tests**

`backend/apps/events/test_budget_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python manage.py test apps.events.test_budget_api`
Expected: ERROR — `cannot import name 'BudgetItem'`.

- [ ] **Step 3: Model**

Append to `backend/apps/events/models.py`:

```python
class BudgetItem(models.Model):
    """A planned or actual event cost, optionally owed to a vendor."""

    class Category(models.TextChoices):
        VENUE = "venue", "Venue"
        CATERING = "catering", "Catering"
        EQUIPMENT = "equipment", "Equipment"
        MARKETING = "marketing", "Marketing"
        TRANSPORT = "transport", "Transport"
        STAFF = "staff", "Staff"
        OTHER = "other", "Other"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="budget_items",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.CharField(max_length=200)
    vendor = models.CharField(max_length=120, blank=True)
    planned_amount = models.DecimalField(max_digits=12, decimal_places=2)
    actual_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    paid = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budget_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "id"]

    def __str__(self):
        return f"{self.description} ({self.event.name})"
```

Run: `../.venv/bin/python manage.py makemigrations events -n budgetitem`
Expected: creates `0015_budgetitem.py`.

- [ ] **Step 4: Views and URLs**

`backend/apps/events/finance_views.py`:

```python
"""Budget, payment and summary endpoints for event leads."""

from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from .models import BudgetItem
from .permissions import lead_event_or_deny


class BudgetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItem
        fields = [
            "id",
            "category",
            "description",
            "vendor",
            "planned_amount",
            "actual_amount",
            "paid",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class BudgetItemListCreateView(generics.ListCreateAPIView):
    serializer_class = BudgetItemSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return lead_event_or_deny(self.kwargs["event_id"], self.request.user)

    def get_queryset(self):
        return self.get_event().budget_items.all()

    def perform_create(self, serializer):
        serializer.save(event=self.get_event(), created_by=self.request.user)


class BudgetItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BudgetItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        event = lead_event_or_deny(self.kwargs["event_id"], self.request.user)
        return event.budget_items.all()
```

In `backend/apps/events/urls.py` add:

```python
from .finance_views import BudgetItemDetailView, BudgetItemListCreateView
```

```python
    path(
        "<int:event_id>/budget/",
        BudgetItemListCreateView.as_view(),
        name="event-budget",
    ),
    path(
        "<int:event_id>/budget/<int:pk>/",
        BudgetItemDetailView.as_view(),
        name="event-budget-item",
    ),
```

- [ ] **Step 5: Run tests**

Run: `../.venv/bin/python manage.py test apps.events.test_budget_api`
Expected: `Ran 3 tests ... OK`.

- [ ] **Step 6: Commit**

```bash
PATH="/usr/bin:$PATH" git add backend/apps/events
PATH="/usr/bin:$PATH" git commit -m "feat(events): budget line items with vendor and paid tracking"
```

(API docs for budget, summary and payments are written together in Task 7.)

---

### Task 7: Summary and payments endpoints

**Files:**
- Create: `backend/apps/events/services/summary.py`
- Modify: `backend/apps/events/finance_views.py`
- Modify: `backend/apps/events/urls.py`
- Test: `backend/apps/events/test_summary_api.py`

**Interfaces:**
- Consumes: `BudgetItem` (Task 6), `Feedback`, `Payment`, `RegistrationTicket`, `lead_event_or_deny`.
- Produces: `event_currency(event) -> str`; `event_summary(event) -> dict` exactly matching the spec's JSON shape (decimal amounts as strings with 2 places).

- [ ] **Step 1: Write the failing tests**

`backend/apps/events/test_summary_api.py`:

```python
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    BudgetItem,
    Event,
    EventMembership,
    EventRegistration,
    Feedback,
    Payment,
    RegistrationTicket,
    TicketType,
)

User = get_user_model()


class SummaryAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="org")
        self.manager = User.objects.create_user(username="mgr")
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Summary Event",
            category=Event.Category.CONCERT,
            date=timezone.localdate(),
            start_time="18:00",
            end_time="23:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )
        EventMembership.objects.create(
            event=self.event, user=self.manager,
            role=EventMembership.Role.MANAGER,
        )
        self.url = f"/api/events/{self.event.id}/summary/"

    def register(self, username, reg_status, ticket=None, amount=None):
        return EventRegistration.objects.create(
            event=self.event,
            user=User.objects.create_user(username=username),
            status=reg_status,
            ticket_type=ticket,
            amount_due=amount,
            currency="UGX" if amount else "",
        )

    def test_empty_event(self):
        self.client.force_authenticate(user=self.manager)
        data = self.client.get(self.url).data

        self.assertEqual(data["currency"], "UGX")
        self.assertEqual(data["attendance"]["rate"], 0.0)
        self.assertEqual(data["payments"]["collected"], "0.00")
        self.assertEqual(data["budget"]["net"], "0.00")
        self.assertIsNone(data["feedback"]["average_rating"])

    def test_aggregates(self):
        vip = TicketType.objects.create(
            event=self.event, name="VIP", price=Decimal("50000"), currency="UGX",
        )
        paid = self.register("a", EventRegistration.Status.CONFIRMED, vip, Decimal("50000"))
        free = self.register("b", EventRegistration.Status.CONFIRMED)
        self.register("c", EventRegistration.Status.PAYMENT_PENDING, vip, Decimal("50000"))
        self.register("d", EventRegistration.Status.CANCELLED)

        Payment.objects.create(
            registration=paid, reference="r1", method="mobile_money",
            amount=Decimal("50000"), currency="UGX", status="completed",
        )
        Payment.objects.create(
            registration=paid, reference="r2", method="mobile_money",
            amount=Decimal("50000"), currency="UGX", status="failed",
        )
        RegistrationTicket.objects.create(registration=paid, checked_in_at=timezone.now())
        RegistrationTicket.objects.create(registration=free)
        BudgetItem.objects.create(
            event=self.event, category="venue", description="Hall",
            planned_amount=Decimal("30000"), actual_amount=Decimal("35000"), paid=True,
        )
        BudgetItem.objects.create(
            event=self.event, category="catering", description="Food",
            planned_amount=Decimal("10000"),
        )
        Feedback.objects.create(event=self.event, attendee=paid.user, rating=5)
        Feedback.objects.create(event=self.event, attendee=free.user, rating=3)

        self.client.force_authenticate(user=self.organizer)
        data = self.client.get(self.url).data

        regs = data["registrations"]
        self.assertEqual(
            (regs["confirmed"], regs["payment_pending"], regs["cancelled"]), (2, 1, 1),
        )
        self.assertEqual(regs["by_ticket_type"], [{"name": "VIP", "count": 2}])
        self.assertEqual(sum(d["count"] for d in regs["by_day"]), 4)
        self.assertEqual(
            data["attendance"], {"checked_in": 1, "confirmed": 2, "rate": 0.5},
        )
        self.assertEqual(
            data["payments"],
            {"collected": "50000.00", "pending": "50000.00", "failed_count": 1},
        )
        self.assertEqual(
            data["budget"],
            {"planned": "40000.00", "actual": "35000.00",
             "unpaid": "10000.00", "net": "15000.00"},
        )
        self.assertEqual(data["feedback"], {"average_rating": 4.0, "count": 2})

    def test_payments_list_is_organizer_only(self):
        paid = self.register("a", EventRegistration.Status.CONFIRMED, amount=Decimal("1000"))
        Payment.objects.create(
            registration=paid, reference="r1", method="card",
            amount=Decimal("1000"), currency="UGX", status="completed",
        )
        url = f"/api/events/{self.event.id}/payments/"

        self.client.force_authenticate(user=self.manager)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["attendee"], "a")
        self.assertEqual(response.data[0]["status"], "completed")
```

`Feedback.attendee` is a User, so the test passes `paid.user` / `free.user` (not the registrations).

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python manage.py test apps.events.test_summary_api`
Expected: FAIL — `404` for `/summary/` and `/payments/`.

- [ ] **Step 3: Summary service**

`backend/apps/events/services/summary.py`:

```python
"""Read-only aggregates for the Payments, Analytics and Budget pages."""

from decimal import Decimal

from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import Coalesce, TruncDate

from ..models import (
    EventRegistration,
    Payment,
    RegistrationTicket,
    TicketType,
)

ZERO = Decimal("0.00")


def money(value):
    return f"{(value or ZERO):.2f}"


def event_currency(event):
    ticket = (
        TicketType.objects.filter(event=event, is_active=True)
        .order_by("pk")
        .first()
    )
    return ticket.currency if ticket else "UGX"


def event_summary(event):
    registrations = EventRegistration.objects.filter(event=event)
    by_status = dict(
        registrations.values_list("status").annotate(n=Count("id"))
    )
    confirmed = by_status.get(EventRegistration.Status.CONFIRMED, 0)

    checked_in = RegistrationTicket.objects.filter(
        registration__event=event,
        checked_in_at__isnull=False,
    ).count()

    payments = Payment.objects.filter(registration__event=event)
    collected = payments.filter(
        status=Payment.Status.COMPLETED,
    ).aggregate(total=Sum("amount"))["total"]
    pending = registrations.filter(
        status=EventRegistration.Status.PAYMENT_PENDING,
    ).aggregate(total=Sum("amount_due"))["total"]

    items = event.budget_items.all()
    planned = items.aggregate(total=Sum("planned_amount"))["total"]
    actual = items.aggregate(total=Sum("actual_amount"))["total"]
    unpaid = items.filter(paid=False).aggregate(
        total=Sum(Coalesce("actual_amount", "planned_amount"))
    )["total"]

    feedback = event.feedback.aggregate(
        average=Avg("rating"),
        count=Count("id"),
    )

    return {
        "currency": event_currency(event),
        "registrations": {
            "confirmed": confirmed,
            "payment_pending": by_status.get(
                EventRegistration.Status.PAYMENT_PENDING, 0
            ),
            "cancelled": by_status.get(EventRegistration.Status.CANCELLED, 0),
            "by_day": [
                {"date": row["day"].isoformat(), "count": row["count"]}
                for row in registrations
                .annotate(day=TruncDate("registered_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            ],
            "by_ticket_type": [
                {"name": row["name"], "count": row["count"]}
                for row in registrations
                .filter(ticket_type__isnull=False)
                .values(name=F("ticket_type__name"))
                .annotate(count=Count("id"))
                .order_by("name")
            ],
        },
        "attendance": {
            "checked_in": checked_in,
            "confirmed": confirmed,
            "rate": round(checked_in / confirmed, 3) if confirmed else 0.0,
        },
        "payments": {
            "collected": money(collected),
            "pending": money(pending),
            "failed_count": payments.filter(
                status=Payment.Status.FAILED,
            ).count(),
        },
        "budget": {
            "planned": money(planned),
            "actual": money(actual),
            "unpaid": money(unpaid),
            "net": money((collected or ZERO) - (actual or ZERO)),
        },
        "feedback": {
            "average_rating": (
                round(feedback["average"], 1)
                if feedback["average"] is not None
                else None
            ),
            "count": feedback["count"],
        },
    }
```

Note `by_ticket_type` counts every registration with a ticket type, including pending and cancelled (the test expects 2 for VIP: one confirmed, one pending).

- [ ] **Step 4: Views and URLs**

Append to `backend/apps/events/finance_views.py`:

```python
from django.http import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .services.summary import event_summary


class EventSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        return Response(event_summary(event))


class EventPaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        if event.organizer_id != request.user.pk:
            raise PermissionDenied("Only the organizer can view payments.")

        payments = (
            Payment.objects.filter(registration__event=event)
            .select_related("registration__user")
            .order_by("-created_at")
        )
        return Response([
            {
                "id": p.id,
                "reference": p.reference,
                "attendee": (
                    p.registration.user.get_full_name()
                    or p.registration.user.username
                ),
                "method": p.method,
                "amount": f"{p.amount:.2f}",
                "currency": p.currency,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in payments
        ])
```

Move the new imports to the top of `finance_views.py` alongside the existing ones (drop the unused `Http404`).

In `backend/apps/events/urls.py`, extend the finance import to `from .finance_views import BudgetItemDetailView, BudgetItemListCreateView, EventPaymentListView, EventSummaryView` and add:

```python
    path(
        "<int:event_id>/summary/",
        EventSummaryView.as_view(),
        name="event-summary",
    ),
    path(
        "<int:event_id>/payments/",
        EventPaymentListView.as_view(),
        name="event-payments",
    ),
```

- [ ] **Step 5: Run tests**

Run: `../.venv/bin/python manage.py test apps.events.test_summary_api apps.events.test_budget_api`
Expected: all pass.

- [ ] **Step 6: Document and commit**

In `docs/api/README.md`, add before `## Team`:

```markdown
## Budget, payments and analytics

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET, POST | `/api/events/<event_id>/budget/` | organizer or manager | Budget lines: `category`, `description`, `vendor`, `planned_amount`, `actual_amount`, `paid` |
| GET, PUT, PATCH, DELETE | `/api/events/<event_id>/budget/<id>/` | organizer or manager | Manage one line |
| GET | `/api/events/<event_id>/summary/` | organizer or manager | Registrations (by status, day, ticket type), attendance and check-in rate, payments collected and pending, budget planned/actual/unpaid/net, average rating |
| GET | `/api/events/<event_id>/payments/` | organizer | Payment list with attendee, amount, method and status |

Budget categories: venue, catering, equipment, marketing, transport, staff, other. Net = payments collected − actual spend.
```

```bash
PATH="/usr/bin:$PATH" git add backend/apps/events docs/api/README.md
PATH="/usr/bin:$PATH" git commit -m "feat(events): event summary and payments list endpoints"
```

---

### Task 8: Payments, Analytics and Budget pages

**Files:**
- Create: `frontend/src/lib/finance.js`
- Create: `frontend/src/pages/PaymentsPage.jsx`, `frontend/src/pages/AnalyticsPage.jsx`, `frontend/src/pages/BudgetPage.jsx`
- Modify: `frontend/src/components/organizer/navigation.js`
- Modify: `frontend/src/layouts/OrganizerLayout.jsx`

**Interfaces:**
- Consumes: Task 6–7 endpoints; `EventPicker` (Task 2); summary shape from Task 7.

- [ ] **Step 1: API helpers**

`frontend/src/lib/finance.js`:

```js
import { apiRequest } from './auth'

export function getEventSummary(eventId) {
  return apiRequest(`/api/events/${eventId}/summary/`)
}

export function getEventPayments(eventId) {
  return apiRequest(`/api/events/${eventId}/payments/`)
}

export function getBudgetItems(eventId) {
  return apiRequest(`/api/events/${eventId}/budget/`)
}

export function createBudgetItem(eventId, item) {
  return apiRequest(`/api/events/${eventId}/budget/`, {
    method: 'POST',
    body: JSON.stringify(item),
  })
}

export function updateBudgetItem(eventId, itemId, changes) {
  return apiRequest(`/api/events/${eventId}/budget/${itemId}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deleteBudgetItem(eventId, itemId) {
  return apiRequest(`/api/events/${eventId}/budget/${itemId}/`, {
    method: 'DELETE',
  })
}

export function formatMoney(value, currency) {
  const amount = Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })
  return `${currency} ${amount}`
}
```

- [ ] **Step 2: Payments page**

`frontend/src/pages/PaymentsPage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { AlertCircle, CircleDollarSign, Clock } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import StatCard from '../components/StatCard'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import { formatDateTime } from '../lib/format'
import { formatMoney, getEventPayments, getEventSummary } from '../lib/finance'

const STATUSES = ['all', 'completed', 'pending', 'processing', 'failed', 'cancelled']

export default function PaymentsPage() {
  const [event, setEvent] = useState(null)
  const [summary, setSummary] = useState(null)
  const [payments, setPayments] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!event) return
    let active = true
    setLoading(true)
    setError('')

    Promise.all([getEventSummary(event.id), getEventPayments(event.id)])
      .then(([s, p]) => {
        if (!active) return
        setSummary(s)
        setPayments(p)
      })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event])

  const shown = filter === 'all' ? payments : payments.filter((p) => p.status === filter)

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Ticket revenue
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Payments
        </h1>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="payments-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {summary && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Collected" value={formatMoney(summary.payments.collected, summary.currency)} icon={CircleDollarSign} />
            <StatCard label="Pending" value={formatMoney(summary.payments.pending, summary.currency)} icon={Clock} caption={`${summary.registrations.payment_pending} registrations awaiting payment`} />
            <StatCard label="Failed payments" value={summary.payments.failed_count} icon={AlertCircle} accent="bg-red-50 text-red-700" />
          </div>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Transactions</h2>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                aria-label="Filter by status"
                className="rounded-xl border border-border-soft bg-white px-3 py-2 text-sm"
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            {!shown.length && <p className="mt-4 text-sm text-text-muted">No payments.</p>}
            {shown.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-text-muted">
                    <tr>
                      <th className="py-2 pr-4">Attendee</th>
                      <th className="py-2 pr-4">Amount</th>
                      <th className="py-2 pr-4">Method</th>
                      <th className="py-2 pr-4">Status</th>
                      <th className="py-2">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EDF1EA]">
                    {shown.map((p) => (
                      <tr key={p.id}>
                        <td className="py-2 pr-4">{p.attendee}</td>
                        <td className="py-2 pr-4">{formatMoney(p.amount, p.currency)}</td>
                        <td className="py-2 pr-4">{p.method.replace('_', ' ')}</td>
                        <td className="py-2 pr-4">{p.status}</td>
                        <td className="py-2">{formatDateTime(p.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Analytics page**

`frontend/src/pages/AnalyticsPage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ScanLine, Star, UserCheck, Users } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import StatCard from '../components/StatCard'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import { getEventSummary } from '../lib/finance'

const GREEN = '#58761B'

function ChartCard({ title, children, empty }) {
  return (
    <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      {empty
        ? <p className="mt-4 text-sm text-text-muted">No data yet.</p>
        : <div className="mt-4 h-64">{children}</div>}
    </section>
  )
}

export default function AnalyticsPage() {
  const [event, setEvent] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!event) return
    let active = true
    setLoading(true)
    setError('')

    getEventSummary(event.id)
      .then((s) => { if (active) setSummary(s) })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event])

  const regs = summary?.registrations
  const total = regs ? regs.confirmed + regs.payment_pending + regs.cancelled : 0

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Event performance
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Analytics
        </h1>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="analytics-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {summary && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Registrations" value={total} icon={Users} caption={`${regs.cancelled} cancelled`} />
            <StatCard label="Confirmed" value={regs.confirmed} icon={UserCheck} caption={`${regs.payment_pending} awaiting payment`} />
            <StatCard label="Check-in rate" value={`${Math.round(summary.attendance.rate * 100)}%`} icon={ScanLine} caption={`${summary.attendance.checked_in} of ${summary.attendance.confirmed} checked in`} />
            <StatCard label="Average rating" value={summary.feedback.average_rating ?? '—'} icon={Star} caption={`${summary.feedback.count} responses`} />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <ChartCard title="Registrations per day" empty={!regs.by_day.length}>
              <ResponsiveContainer>
                <LineChart data={regs.by_day}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EDF1EA" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke={GREEN} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Registrations by ticket type" empty={!regs.by_ticket_type.length}>
              <ResponsiveContainer>
                <BarChart data={regs.by_ticket_type}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EDF1EA" />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="count" fill={GREEN} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Budget page**

`frontend/src/pages/BudgetPage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import {
  createBudgetItem,
  deleteBudgetItem,
  formatMoney,
  getBudgetItems,
  getEventSummary,
  updateBudgetItem,
} from '../lib/finance'

const CATEGORIES = ['venue', 'catering', 'equipment', 'marketing', 'transport', 'staff', 'other']
const EMPTY_ITEM = { category: 'venue', description: '', vendor: '', planned_amount: '', actual_amount: '' }
const INPUT = 'rounded-xl border border-border-soft bg-white px-3 py-2 text-sm outline-none focus:border-[#58761B]'

export default function BudgetPage() {
  const [event, setEvent] = useState(null)
  const [items, setItems] = useState([])
  const [summary, setSummary] = useState(null)
  const [draft, setDraft] = useState(EMPTY_ITEM)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!event) return
    let active = true
    setLoading(true)

    Promise.all([getBudgetItems(event.id), getEventSummary(event.id)])
      .then(([list, s]) => {
        if (!active) return
        setItems(list)
        setSummary(s)
      })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event, refreshKey])

  async function run(action) {
    setSaving(true)
    setError('')
    try {
      await action()
      setRefreshKey((k) => k + 1)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSaving(false)
    }
  }

  function handleAdd(e) {
    e.preventDefault()
    run(async () => {
      await createBudgetItem(event.id, {
        ...draft,
        actual_amount: draft.actual_amount === '' ? null : draft.actual_amount,
      })
      setDraft(EMPTY_ITEM)
    })
  }

  const currency = summary?.currency || 'UGX'
  const money = (v) => formatMoney(v, currency)
  const net = Number(summary?.budget.net || 0)

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Event finances
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Budget
        </h1>
        <p className="mt-3 max-w-2xl text-text-muted">
          Plan costs, record what was spent and track which vendors are still unpaid.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="budget-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {summary && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {[
              ['Planned', money(summary.budget.planned)],
              ['Actual spend', money(summary.budget.actual)],
              ['Ticket revenue', money(summary.payments.collected)],
              ['Net', money(summary.budget.net)],
              ['Unpaid vendors', money(summary.budget.unpaid)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm">
                <p className="text-sm text-text-muted">{label}</p>
                <p className={`mt-2 text-2xl font-bold ${label === 'Net' && net < 0 ? 'text-red-700' : 'text-[#1A3F22]'}`}>
                  {value}
                </p>
              </div>
            ))}
          </div>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold">Budget lines</h2>

            <form onSubmit={handleAdd} className="mt-4 grid gap-2 md:grid-cols-[auto_1fr_1fr_auto_auto_auto]">
              <select aria-label="Category" value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })} className={INPUT}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <input aria-label="Description" required placeholder="Description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} className={INPUT} />
              <input aria-label="Vendor" placeholder="Vendor (optional)" value={draft.vendor} onChange={(e) => setDraft({ ...draft, vendor: e.target.value })} className={INPUT} />
              <input aria-label="Planned amount" required type="number" min="0" step="0.01" placeholder="Planned" value={draft.planned_amount} onChange={(e) => setDraft({ ...draft, planned_amount: e.target.value })} className={INPUT} />
              <input aria-label="Actual amount" type="number" min="0" step="0.01" placeholder="Actual" value={draft.actual_amount} onChange={(e) => setDraft({ ...draft, actual_amount: e.target.value })} className={INPUT} />
              <button type="submit" disabled={saving} className="rounded-xl bg-[#58761B] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
                Add
              </button>
            </form>

            {!items.length && <p className="mt-4 text-sm text-text-muted">No budget lines yet.</p>}
            {items.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-text-muted">
                    <tr>
                      <th className="py-2 pr-4">Category</th>
                      <th className="py-2 pr-4">Description</th>
                      <th className="py-2 pr-4">Vendor</th>
                      <th className="py-2 pr-4">Planned</th>
                      <th className="py-2 pr-4">Actual</th>
                      <th className="py-2 pr-4">Paid</th>
                      <th className="py-2"><span className="sr-only">Delete</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EDF1EA]">
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td className="py-2 pr-4">{item.category}</td>
                        <td className="py-2 pr-4">{item.description}</td>
                        <td className="py-2 pr-4">{item.vendor || '—'}</td>
                        <td className="py-2 pr-4">{money(item.planned_amount)}</td>
                        <td className="py-2 pr-4">{item.actual_amount === null ? '—' : money(item.actual_amount)}</td>
                        <td className="py-2 pr-4">
                          <input
                            type="checkbox"
                            aria-label={`Mark ${item.description} paid`}
                            checked={item.paid}
                            disabled={saving}
                            onChange={() => run(() => updateBudgetItem(event.id, item.id, { paid: !item.paid }))}
                          />
                        </td>
                        <td className="py-2">
                          <button
                            type="button"
                            aria-label={`Delete ${item.description}`}
                            disabled={saving}
                            onClick={() => window.confirm('Delete this budget line?') && run(() => deleteBudgetItem(event.id, item.id))}
                            className="text-red-700 disabled:opacity-50"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Navigation and routes**

In `frontend/src/components/organizer/navigation.js`: add `Wallet` to the lucide import list and insert after the Payments entry:

```js
  { name: 'Budget', path: 'budget', icon: Wallet },
```

In `frontend/src/layouts/OrganizerLayout.jsx`: import `PaymentsPage`, `AnalyticsPage`, `BudgetPage`; add `'payments'`, `'analytics'`, `'budget'` to `builtPaths`; add routes:

```jsx
            <Route path="payments" element={<PaymentsPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="budget" element={<BudgetPage />} />
```

After this, every sidebar path is built, so the `navigation.slice(1).filter(...).map(...)` placeholder block renders nothing; leave it (future sidebar entries fall back to the placeholder).

- [ ] **Step 6: Verify**

Run from `frontend/`: `npm run lint && npm run build`
Expected: clean.

Manual: `/operations/payments`, `/operations/analytics`, `/operations/budget` load for an organizer; adding a budget line updates Planned and Unpaid; ticking Paid reduces Unpaid.

- [ ] **Step 7: Commit**

```bash
PATH="/usr/bin:$PATH" git add frontend/src
PATH="/usr/bin:$PATH" git commit -m "feat(frontend): Payments, Analytics and Budget pages"
```

---

### Task 9: Extract registration into a shared service

**Files:**
- Create: `backend/apps/events/services/registration.py`
- Modify: `backend/apps/events/registration_views.py` (`EventRegistrationView.post`)

**Interfaces:**
- Produces: `register_for_event(event_id, user, ticket_type_id=None) -> EventRegistration`; `RegistrationError(detail: str, http_status: int)` with attributes `.detail`, `.http_status`. Raises `Http404` when the event does not exist.

This is a pure refactor: existing tests (`test_registration_api`, `test_registration_concurrency`, `test_ticket_types_api`, `test_payments_api`, `test_my_registrations_api`) are the safety net and must pass unchanged.

- [ ] **Step 1: Baseline**

Run: `../.venv/bin/python manage.py test apps.events`
Expected: OK. Note the test count.

- [ ] **Step 2: Service**

`backend/apps/events/services/registration.py`:

```python
"""Event registration shared by the web API and USSD."""

from django.db import IntegrityError, OperationalError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import Event, EventRegistration, TicketType

HELD = (
    EventRegistration.Status.CONFIRMED,
    EventRegistration.Status.PAYMENT_PENDING,
)


class RegistrationError(Exception):
    def __init__(self, detail, http_status):
        super().__init__(detail)
        self.detail = detail
        self.http_status = http_status


def register_for_event(event_id, user, ticket_type_id=None):
    """Register user for a published event, respecting capacity."""
    try:
        with transaction.atomic():
            event = get_object_or_404(
                Event.objects.select_for_update(), pk=event_id,
            )

            if event.status != Event.Status.PUBLISHED:
                raise RegistrationError("Registration is not open.", 400)

            if event.date < timezone.localdate():
                raise RegistrationError("This event has already passed.", 400)

            active_ticket_types = TicketType.objects.filter(
                event=event, is_active=True,
            )
            ticket_type = None
            amount_due = None
            currency = ""

            if active_ticket_types.exists():
                if not ticket_type_id:
                    raise RegistrationError("Select a ticket type.", 400)

                try:
                    ticket_type = active_ticket_types.filter(
                        pk=ticket_type_id,
                    ).first()
                except (ValueError, TypeError):
                    ticket_type = None

                if ticket_type is None:
                    raise RegistrationError(
                        "Select a valid ticket type for this event.", 400,
                    )

                amount_due = ticket_type.price
                currency = ticket_type.currency

            registration_status = (
                EventRegistration.Status.CONFIRMED
                if amount_due is None or amount_due == 0
                else EventRegistration.Status.PAYMENT_PENDING
            )

            existing = EventRegistration.objects.filter(
                event=event, user=user,
            ).first()

            if existing and existing.status in HELD:
                raise RegistrationError("You are already registered.", 409)

            held_count = EventRegistration.objects.filter(
                event=event, status__in=HELD,
            ).count()

            if event.capacity is not None and held_count >= event.capacity:
                raise RegistrationError("This event is fully booked.", 409)

            if existing:
                existing.ticket_type = ticket_type
                existing.amount_due = amount_due
                existing.currency = currency
                existing.status = registration_status
                existing.save(
                    update_fields=[
                        "ticket_type",
                        "amount_due",
                        "currency",
                        "status",
                        "updated_at",
                    ]
                )
                return existing

            return EventRegistration.objects.create(
                event=event,
                user=user,
                ticket_type=ticket_type,
                amount_due=amount_due,
                currency=currency,
                status=registration_status,
            )

    except IntegrityError:
        raise RegistrationError("Registration conflict. Please retry.", 409)
    except OperationalError:
        raise RegistrationError("Registration is busy. Please retry.", 503)
```

- [ ] **Step 3: Thin the view**

In `backend/apps/events/registration_views.py`, replace the entire `def post(self, request, event_id): ...` method of `EventRegistrationView` with:

```python
    def post(self, request, event_id):
        try:
            registration = register_for_event(
                event_id,
                request.user,
                ticket_type_id=request.data.get("ticket_type_id"),
            )
        except RegistrationError as exc:
            return Response({"detail": exc.detail}, status=exc.http_status)

        return Response(
            EventRegistrationSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )
```

Add `from .services.registration import RegistrationError, register_for_event` to the imports. Remove imports that became unused in this file (`IntegrityError`, `OperationalError`, and `TicketType` if no other code in the file uses it; keep `transaction` and `timezone` only if still used elsewhere in the file — check with `grep -n "transaction\.\|timezone\.\|TicketType" backend/apps/events/registration_views.py`).

- [ ] **Step 4: Run tests**

Run: `../.venv/bin/python manage.py test apps.events`
Expected: OK with the same test count as Step 1.

- [ ] **Step 5: Commit**

```bash
PATH="/usr/bin:$PATH" git add backend/apps/events
PATH="/usr/bin:$PATH" git commit -m "refactor(events): move registration rules into a shared service"
```

---

### Task 10: USSD "4. Register for an event"

**Files:**
- Modify: `backend/apps/ussd/views.py`
- Test: `backend/apps/ussd/tests.py` (append class)

**Interfaces:**
- Consumes: `register_for_event`, `RegistrationError` (Task 9); `get_public_event` (existing); `send_sms` (existing); `settings.FRONTEND_BASE_URL`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/ussd/tests.py`:

```python
from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings


@override_settings(FRONTEND_BASE_URL="https://tuviora.test")
class USSDRegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("ussd-callback")
        self.phone = "+256712345678"
        organizer = get_user_model().objects.create_user(username="organizer")
        self.attendee = get_user_model().objects.create_user(username="attendee")
        self.preference = SMSPreference.objects.create(
            user=self.attendee, phone_number=self.phone, sms_enabled=True,
        )
        self.event = Event.objects.create(
            organizer=organizer,
            name="Free Workshop",
            category=Event.Category.WORKSHOP,
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            venue="Kampala",
            status=Event.Status.PUBLISHED,
        )

    def send(self, text, phone=None):
        return self.client.post(self.url, {
            "sessionId": "s1",
            "serviceCode": "*384*123#",
            "phoneNumber": phone or self.phone,
            "text": text,
        }).content.decode()

    def test_menu_lists_registration(self):
        self.assertIn("4. Register for an event", self.send(""))

    @patch("apps.ussd.views.send_sms")
    def test_registers_and_confirms_by_sms(self, send_sms):
        e = self.event.pk
        self.assertIn("CON Enter the event ID", self.send("4"))
        self.assertIn("CON Register for Free Workshop", self.send(f"4*{e}"))

        with self.captureOnCommitCallbacks(execute=True):
            reply = self.send(f"4*{e}*1")

        self.assertEqual(reply, "END You're registered for Free Workshop.")
        registration = EventRegistration.objects.get()
        self.assertEqual(registration.status, EventRegistration.Status.CONFIRMED)
        send_sms.assert_called_once()
        self.assertEqual(send_sms.call_args.args[0], self.phone)

    @patch("apps.ussd.views.send_sms")
    def test_no_sms_without_consent(self, send_sms):
        self.preference.sms_enabled = False
        self.preference.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.send(f"4*{self.event.pk}*1")
        self.assertTrue(EventRegistration.objects.exists())
        send_sms.assert_not_called()

    def test_free_ticket_type_is_used(self):
        free = TicketType.objects.create(event=self.event, name="General", price=Decimal("0"))
        TicketType.objects.create(event=self.event, name="VIP", price=Decimal("10000"))
        self.send(f"4*{self.event.pk}*1")
        self.assertEqual(EventRegistration.objects.get().ticket_type, free)

    def test_decline(self):
        self.assertEqual(self.send(f"4*{self.event.pk}*2"), "END Registration cancelled.")
        self.assertFalse(EventRegistration.objects.exists())

    def test_unknown_phone(self):
        self.assertEqual(
            self.send(f"4*{self.event.pk}", phone="+256700000001"),
            "END No Tuviora account uses this phone. "
            "Sign up at https://tuviora.test/signup and add this number.",
        )

    def test_paid_event(self):
        TicketType.objects.create(event=self.event, name="VIP", price=Decimal("10000"))
        self.assertEqual(
            self.send(f"4*{self.event.pk}"),
            f"END This event requires payment. Register at https://tuviora.test/events/{self.event.pk}.",
        )

    def test_full_event(self):
        self.event.capacity = 0
        self.event.save()
        self.assertEqual(self.send(f"4*{self.event.pk}*1"), "END This event is fully booked.")

    def test_already_registered(self):
        EventRegistration.objects.create(
            event=self.event, user=self.attendee,
            status=EventRegistration.Status.CONFIRMED,
        )
        self.assertEqual(self.send(f"4*{self.event.pk}*1"), "END You are already registered.")

    def test_unknown_event(self):
        self.assertEqual(self.send("4*99999"), "END Published event not found.")
        self.assertEqual(self.send("4*abc"), "END Invalid event ID. Please dial again.")
```

Check `Event.capacity` allows `0` (`grep -n "capacity" backend/apps/events/models.py`); if it has a `MinValueValidator(1)`, that only affects forms/serializers — `save()` still stores 0, so the test is valid.

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python manage.py test apps.ussd`
Expected: the new tests FAIL.

- [ ] **Step 3: Implement**

In `backend/apps/ussd/views.py`:

1. Add imports:

```python
from django.conf import settings
from django.db import transaction

from apps.events.models import TicketType
from apps.events.services.registration import (
    RegistrationError,
    register_for_event,
)
from apps.sms.models import SMSPreference
from apps.sms.services.sms_service import SMSServiceError, send_sms
```

2. Update `MAIN_MENU` to insert `"4. Register for an event\n"` between option 3 and option 5.

3. Add above `ussd_callback`:

```python
def register_event(parts, phone):
    """Option 4: register an existing account for a free event."""
    if len(parts) == 1:
        return reply("CON", "Enter the event ID:")
    if not parts[1].isdigit():
        return reply("END", "Invalid event ID. Please dial again.")

    site = settings.FRONTEND_BASE_URL
    preference = (
        SMSPreference.objects.select_related("user")
        .filter(phone_number=phone)
        .first()
    )
    if preference is None:
        return reply(
            "END",
            "No Tuviora account uses this phone. "
            f"Sign up at {site}/signup and add this number.",
        )

    event = get_public_event(parts[1])
    if event is None:
        return reply("END", "Published event not found.")

    ticket_types = TicketType.objects.filter(event=event, is_active=True)
    ticket_type = None
    if ticket_types.exists():
        ticket_type = ticket_types.filter(price=0).order_by("price", "pk").first()
        if ticket_type is None:
            return reply(
                "END",
                f"This event requires payment. Register at {site}/events/{event.pk}.",
            )

    if len(parts) == 2:
        return reply(
            "CON",
            f"Register for {event.name}, {event.date:%d %b} "
            f"{event.start_time:%H:%M}?\n1. Yes\n2. No",
        )
    if parts[2] != "1":
        return reply("END", "Registration cancelled.")

    try:
        register_for_event(
            event.pk,
            preference.user,
            ticket_type_id=ticket_type.pk if ticket_type else None,
        )
    except RegistrationError as exc:
        return reply("END", exc.detail)

    if preference.sms_enabled:
        message = (
            f"You're registered for {event.name} on {event.date:%d %b %Y} "
            f"at {event.start_time:%H:%M}, {event.venue or 'online'}."
        )

        def confirm():
            try:
                send_sms(phone, message)
            except (SMSServiceError, ValueError):
                pass  # SMS failure never undoes the registration.

        transaction.on_commit(confirm)

    return reply("END", f"You're registered for {event.name}.")
```

4. In `ussd_callback`, before the `if parts[0] == "5":` branch, add:

```python
    if parts[0] == "4":
        return register_event(parts, phone)
```

Note: `transaction.on_commit` runs immediately when not in an atomic block (normal request handling), and inside `captureOnCommitCallbacks` in tests.

- [ ] **Step 4: Run tests**

Run: `../.venv/bin/python manage.py test apps.ussd apps.events`
Expected: all pass.

- [ ] **Step 5: Document and commit**

In `docs/ussd-sandbox.md`, change the opening-menu bullet to list "event information, registration check, staff reporting, registering, rating, and exit", and add:

```markdown
- Choose `4`, enter the ID of a free published event, then `1` to confirm.
  The caller's phone must be saved as the SMS number on a Tuviora account;
  otherwise the reply tells them to sign up online. Paid events reply with the
  web registration link. With SMS consent, a confirmation SMS follows.
```

In the root `README.md`, change the USSD bullet under `### Accessible channels (Africa's Talking)` to:

```markdown
- **USSD:** look up a published event, register for a free event, check your registration status and rate an event from a basic phone. See [USSD sandbox](docs/ussd-sandbox.md).
```

In the same file's `## Core features`: under `### Accessible channels`, change the SMS bullet to `- **SMS:** registration welcome, payment confirmation, organizer announcements, daily event reminders and team messages; always opt-in and disabled by default.`; under `### AI assistance`, change "(no frontend screens yet)" to "(feedback summary on the Feedback page; incident analysis via the API)"; and add a new section after `### Attendance and check-in`:

```markdown
### Budget, payments and analytics

Organizers track planned versus actual costs per budget line (with vendor and paid status), see ticket revenue and pending payments, and view registrations per day, by ticket type, check-in rate and average rating.
```

In `frontend/README.md`, replace the placeholder row `| Payments, Communications, Feedback, Analytics | OrganizerModule placeholder — not yet connected to the backend |` with:

```markdown
| Payments | `PaymentsPage` |
| Budget | `BudgetPage` |
| Communications | `Communications` (SMS announcements) |
| Feedback | `FeedbackPage` (incl. AI summary) |
| Analytics | `AnalyticsPage` |
```

```bash
PATH="/usr/bin:$PATH" git add backend/apps/ussd docs/ussd-sandbox.md README.md frontend/README.md
PATH="/usr/bin:$PATH" git commit -m "feat(ussd): register for free events from a basic phone"
```

---

### Task 11: Full verification

- [ ] **Step 1: Backend**

Run from `backend/`: `../.venv/bin/python manage.py test apps && ../.venv/bin/python manage.py check && ../.venv/bin/python manage.py makemigrations --check --dry-run`
Expected: all tests OK; no issues; "No changes detected".

- [ ] **Step 2: Frontend**

Run from `frontend/`: `npm run lint && npm run build && node src/lib/format.check.mjs`
Expected: clean.

- [ ] **Step 3: Migrate the local database and smoke-test**

Run from `backend/`: `../.venv/bin/python manage.py migrate`, then with the dev servers running, visit Communications, Feedback, Payments, Analytics and Budget under `/operations/`, and exercise USSD options 4 and 5 with `curl -X POST http://127.0.0.1:8000/api/ussd/callback/ -d sessionId=s1 -d serviceCode='*384#' -d phoneNumber=<saved number> -d text=4`.
