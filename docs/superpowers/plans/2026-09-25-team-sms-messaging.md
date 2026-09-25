# Team SMS Messaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the single, attendee-only SMS sender into two audience-scoped
functions — `send_attendee_sms` (rename, no behavior change) and
`send_team_sms` (new) — and give organizers/managers a real endpoint and a
minimal UI control to message their whole event team.

**Architecture:** `apps/sms/services/event_sms_notifications.py` gets a
private `_send_sms_to_users` helper (today's logic, unchanged) behind two
public wrappers. A new DRF `APIView` in `apps/events/team_views.py` resolves
the caller's role via the existing `task_access_for_user` helper (already
used by the voice conference feature) and calls `send_team_sms`. Frontend
gets one text box on the existing `EventTeam.jsx` organizer page.

**Tech Stack:** Django 5 / DRF (existing `apps.sms`, `apps.events`), React 19
(existing `EventTeam.jsx`), no new dependencies.

See design spec: `docs/superpowers/specs/2026-09-25-team-voice-notifications-design.md` (Part 1 only).

## Global Constraints

- No new database table or persisted message history — SMS has none today,
  and this stays consistent (per spec's non-goals).
- Reuse `apps.events.views.task_access_for_user(event, user)` for all
  permission checks — do not write a second permission helper.
- Backend tests use Django's `TestCase` (service layer) and DRF's
  `APITestCase` with `force_authenticate` (API layer) — matching
  `apps/sms/test_event_sms_notifications.py` and
  `apps/events/test_team_api.py`. No pytest.
- Mock `send_sms` at `apps.sms.services.event_sms_notifications.send_sms`
  (where it's imported into, not where it's defined) — matches every
  existing SMS test in this repo.
- Frontend has no test runner configured — the frontend task ends with a
  manual dev-server verification step, not an automated test.
- Run backend tests from `backend/`: `python manage.py test apps.sms apps.events`.

---

### Task 1: Split the SMS service into team/attendee functions

**Files:**
- Modify: `backend/apps/sms/services/event_sms_notifications.py` (full rewrite of its one function)
- Modify: `backend/apps/events/payment_views.py:12` (import) and `:189` (call site)
- Modify: `backend/apps/sms/test_event_sms_notifications.py` (rename references, no new behavior)
- Test: `backend/apps/sms/test_team_sms.py` (new)

**Interfaces:**
- Produces: `send_attendee_sms(user_ids, message) -> {"submitted": int, "failed": int, "skipped": int}` (same shape as today's `send_event_sms`)
- Produces: `send_team_sms(event, message) -> {"submitted": int, "failed": int, "skipped": int}`
- Consumes: `apps.events.models.EventMembership` (existing), `apps.sms.models.SMSPreference` (existing)

- [ ] **Step 1: Write the failing test for `send_team_sms`**

Create `backend/apps/sms/test_team_sms.py`:

```python
"""Tests for team-wide SMS notifications."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.events.models import Event, EventMembership
from apps.sms.models import SMSPreference
from apps.sms.services.event_sms_notifications import send_team_sms


class SendTeamSMSTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="team_sms_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="team_sms_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="team_sms_member",
            password="TestPassword2026!",
        )
        self.outsider = User.objects.create_user(
            username="team_sms_outsider",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Team SMS Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 1),
            start_time=time(9, 0),
            end_time=time(17, 0),
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

        SMSPreference.objects.create(
            user=self.organizer,
            phone_number="+256700000001",
            sms_enabled=True,
        )
        SMSPreference.objects.create(
            user=self.manager,
            phone_number="+256700000002",
            sms_enabled=True,
        )
        SMSPreference.objects.create(
            user=self.member,
            phone_number="+256700000003",
            sms_enabled=True,
        )
        SMSPreference.objects.create(
            user=self.outsider,
            phone_number="+256700000004",
            sms_enabled=True,
        )

    @patch("apps.sms.services.event_sms_notifications.send_sms")
    def test_sends_to_organizer_and_all_members_only(self, mock_send_sms):
        result = send_team_sms(self.event, "Team update")

        called_numbers = {
            call.args[0] for call in mock_send_sms.call_args_list
        }

        self.assertEqual(
            called_numbers,
            {"+256700000001", "+256700000002", "+256700000003"},
        )
        self.assertEqual(
            result,
            {"submitted": 3, "failed": 0, "skipped": 0},
        )

    @patch("apps.sms.services.event_sms_notifications.send_sms")
    def test_does_not_message_users_outside_the_team(self, mock_send_sms):
        send_team_sms(self.event, "Team update")

        called_numbers = {
            call.args[0] for call in mock_send_sms.call_args_list
        }

        self.assertNotIn("+256700000004", called_numbers)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python manage.py test apps.sms.test_team_sms -v 2`
Expected: FAIL — `ImportError: cannot import name 'send_team_sms'`

- [ ] **Step 3: Rewrite the service module**

Replace the full contents of `backend/apps/sms/services/event_sms_notifications.py`:

```python
"""Consent-aware SMS notifications for Tuviora."""

import logging

from apps.events.models import EventMembership
from apps.sms.models import SMSPreference

from .sms_service import SMSServiceError, send_sms

logger = logging.getLogger(__name__)


def _send_sms_to_users(user_ids, message):
    """
    Send an SMS to explicitly selected, opted-in users.

    Callers must verify event membership or attendee registration
    and obtain organizer approval before invoking this function.
    """
    if not isinstance(message, str) or not message.strip():
        raise ValueError("A non-empty SMS message is required.")

    if not user_ids:
        return {
            "submitted": 0,
            "failed": 0,
            "skipped": 0,
        }

    selected_ids = set(user_ids)

    preferences = SMSPreference.objects.filter(
        user_id__in=selected_ids,
        sms_enabled=True,
    ).exclude(
        phone_number="",
    )

    submitted = 0
    failed = 0

    for preference in preferences:
        try:
            send_sms(
                preference.phone_number,
                message.strip(),
            )
            submitted += 1
        except (SMSServiceError, ValueError):
            failed += 1
            logger.warning(
                "Event SMS submission failed for user ID %s.",
                preference.user_id,
            )

    return {
        "submitted": submitted,
        "failed": failed,
        "skipped": len(selected_ids) - submitted - failed,
    }


def send_attendee_sms(user_ids, message):
    """Send an SMS to explicitly selected, opted-in attendees."""
    return _send_sms_to_users(user_ids, message)


def send_team_sms(event, message):
    """Send an SMS to the event organizer and every accepted team member."""
    user_ids = {event.organizer_id}
    user_ids.update(
        EventMembership.objects.filter(event=event)
        .values_list("user_id", flat=True)
    )
    return _send_sms_to_users(user_ids, message)
```

- [ ] **Step 4: Update the one existing caller**

In `backend/apps/events/payment_views.py`, change line 12 from:

```python
from apps.sms.services.event_sms_notifications import send_event_sms
```

to:

```python
from apps.sms.services.event_sms_notifications import send_attendee_sms
```

And change line 189 from:

```python
    send_event_sms([payment.registration.user_id], message)
```

to:

```python
    send_attendee_sms([payment.registration.user_id], message)
```

- [ ] **Step 5: Update the existing test file's references**

In `backend/apps/sms/test_event_sms_notifications.py`, change the import on
line 9 from `send_event_sms` to `send_attendee_sms`, and replace every
`send_event_sms(` call (6 occurrences, inside each test method) with
`send_attendee_sms(`. No other changes — the test bodies and assertions
stay exactly as they are, since `send_attendee_sms` has identical behavior.

- [ ] **Step 6: Run the full SMS and events suites**

Run: `cd backend && python manage.py test apps.sms apps.events`
Expected: PASS — all tests, including the new `test_team_sms.py` and the
renamed `test_event_sms_notifications.py`.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/sms/services/event_sms_notifications.py \
        backend/apps/sms/test_event_sms_notifications.py \
        backend/apps/sms/test_team_sms.py \
        backend/apps/events/payment_views.py
git commit -m "Split SMS notifications into attendee and team-wide senders"
```

---

### Task 2: Message-team API endpoint

**Files:**
- Modify: `backend/apps/events/team_views.py` (add imports + `MessageTeamView`)
- Modify: `backend/apps/events/urls.py` (add import + route)
- Test: `backend/apps/events/test_team_message_api.py` (new)

**Interfaces:**
- Consumes: `send_team_sms(event, message)` from Task 1; `task_access_for_user(event, user)` from `apps/events/views.py` (existing, returns `"organizer"` / `EventMembership.Role` value / `None`)
- Produces: `POST /api/events/<event_id>/team/message/`, URL name `event-team-message`

- [ ] **Step 1: Write the failing API test**

Create `backend/apps/events/test_team_message_api.py`:

```python
"""Tests for the team SMS messaging endpoint."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventMembership


class MessageTeamAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="msg_team_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="msg_team_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="msg_team_member",
            password="TestPassword2026!",
        )
        self.outsider = User.objects.create_user(
            username="msg_team_outsider",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Message Team Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 5),
            start_time=time(9, 0),
            end_time=time(17, 0),
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

        self.url = reverse(
            "event-team-message",
            kwargs={"event_id": self.event.id},
        )

    @patch("apps.events.team_views.send_team_sms")
    def test_organizer_can_message_team(self, mock_send):
        mock_send.return_value = {
            "submitted": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.url,
            {"message": "All hands on deck"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["submitted"], 2)
        mock_send.assert_called_once_with(
            self.event,
            "All hands on deck",
        )

    @patch("apps.events.team_views.send_team_sms")
    def test_manager_can_message_team(self, mock_send):
        mock_send.return_value = {
            "submitted": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            self.url,
            {"message": "Doors open at 8am"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_member_cannot_message_team(self):
        self.client.force_authenticate(self.member)

        response = self.client.post(
            self.url,
            {"message": "Hello"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_gets_not_found(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.post(
            self.url,
            {"message": "Hello"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_blank_message_is_rejected(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(self.url, {"message": "   "})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python manage.py test apps.events.test_team_message_api -v 2`
Expected: FAIL — `NoReverseMatch: 'event-team-message' not found`

- [ ] **Step 3: Add the view**

In `backend/apps/events/team_views.py`, add to the existing imports at the
top of the file:

```python
from django.http import Http404
```

and:

```python
from apps.sms.services.event_sms_notifications import send_team_sms

from .views import task_access_for_user
```

Then append this class at the end of the file:

```python
class MessageTeamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        role = task_access_for_user(event, request.user)

        if role is None:
            raise Http404

        if role not in ("organizer", EventMembership.Role.MANAGER):
            return Response(
                {
                    "detail": (
                        "Only the organizer or event managers "
                        "can message the team."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        message = str(request.data.get("message", "")).strip()

        if not message:
            return Response(
                {"detail": "A non-empty message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(send_team_sms(event, message))
```

- [ ] **Step 4: Wire up the URL**

In `backend/apps/events/urls.py`, change the `team_views` import block from:

```python
from .team_views import (
    EventTeamView,
    EventInvitationView,
    EventInvitationRevokeView,
    InvitationAcceptView,
)
```

to:

```python
from .team_views import (
    EventTeamView,
    EventInvitationView,
    EventInvitationRevokeView,
    InvitationAcceptView,
    MessageTeamView,
)
```

and add this path immediately after the existing `"<int:event_id>/team/"` entry:

```python
    path(
        "<int:event_id>/team/message/",
        MessageTeamView.as_view(),
        name="event-team-message",
    ),
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && python manage.py test apps.events.test_team_message_api -v 2`
Expected: PASS — all 5 tests.

- [ ] **Step 6: Run the full events suite to check for regressions**

Run: `cd backend && python manage.py test apps.events`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/events/team_views.py \
        backend/apps/events/urls.py \
        backend/apps/events/test_team_message_api.py
git commit -m "Add organizer/manager endpoint to message the event team"
```

---

### Task 3: Frontend "Message team" control

**Files:**
- Modify: `frontend/src/lib/team.js` (add `sendTeamMessage`)
- Modify: `frontend/src/pages/EventTeam.jsx` (add state, handler, and a section)

**Interfaces:**
- Consumes: `POST /api/events/<event_id>/team/message/` from Task 2
- Produces: `sendTeamMessage(eventId, message) -> Promise<{submitted, failed, skipped}>`, exported from `frontend/src/lib/team.js`

**Scope note:** This wires the control into `EventTeam.jsx` only — the
organizer-facing team page, which is the only page currently guaranteed to
reach an event a user has access to (`TeamWorkspace.jsx`, the
manager/member-facing page, has no equivalent entry point yet). The backend
endpoint already accepts manager callers; giving managers a UI for it is a
follow-up, not required here.

- [ ] **Step 1: Add the API client function**

In `frontend/src/lib/team.js`, add:

```javascript
export function sendTeamMessage(eventId, message) {
  return apiRequest(`/api/events/${eventId}/team/message/`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}
```

- [ ] **Step 2: Add state and a handler in `EventTeam.jsx`**

Add `sendTeamMessage` to the import from `../lib/team` at the top of
`frontend/src/pages/EventTeam.jsx`:

```javascript
import {
  createEventInvitation,
  getEventInvitations,
  getEventTeam,
  revokeEventInvitation,
  sendTeamMessage,
} from '../lib/team'
```

Add new state alongside the existing `useState` calls (after the
`refreshKey` line):

```javascript
  const [teamMessage, setTeamMessage] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
```

Add this handler alongside `handleInvite`/`handleRevoke`:

```javascript
  async function handleSendTeamMessage(event) {
    event.preventDefault()
    if (!selectedEventId || sendingMessage || !teamMessage.trim()) return

    setSendingMessage(true)
    setError('')
    setNotice('')

    try {
      const result = await sendTeamMessage(
        selectedEventId,
        teamMessage.trim(),
      )
      setTeamMessage('')
      setNotice(
        `Message sent to ${result.submitted} team member`
        + `${result.submitted === 1 ? '' : 's'}.`,
      )
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSendingMessage(false)
    }
  }
```

- [ ] **Step 3: Add the UI section**

In the JSX returned by `EventTeam`, add this new `<section>` immediately
after the closing `</section>` of the "Select an event" block (the one
containing the `#team-event` select), matching the existing card style:

```jsx
      <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-lg font-semibold text-[#1A3F22]">
          Message team
        </h2>
        <p className="mt-1 text-sm text-text-muted">
          Sends an SMS to the organizer and every accepted team member
          for this event.
        </p>
        <form
          onSubmit={handleSendTeamMessage}
          className="mt-4 flex flex-col gap-3 sm:flex-row"
        >
          <textarea
            value={teamMessage}
            onChange={(event) => setTeamMessage(event.target.value)}
            placeholder="Type a message for the team..."
            rows={2}
            className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 outline-none focus:border-[#58761B]"
          />
          <button
            type="submit"
            disabled={
              !selectedEventId || sendingMessage || !teamMessage.trim()
            }
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[#58761B] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            {sendingMessage ? 'Sending...' : 'Send'}
          </button>
        </form>
      </section>
```

- [ ] **Step 4: Manually verify in the browser**

Run the dev servers (backend `python manage.py runserver`, frontend
`npm run dev`), sign in as an organizer with at least one event and one
accepted team member with `sms_enabled=True` and a phone number on file,
open the Event Team page, type a message, and send it. With
`SMS_ENABLED=false` (the local default), expect the request to still
return `200` with `failed` counts reflecting the disabled provider (the
backend already handles this — `send_sms` raises `SMSServiceError`, which
`_send_sms_to_users` catches and counts as `failed`, not a request error).
Confirm the notice banner shows a submitted/failed count and the textarea
clears.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/team.js frontend/src/pages/EventTeam.jsx
git commit -m "Add Message team control to the organizer team page"
```
