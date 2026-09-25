# Critical-Incident Voice Calls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an organizer or event manager trigger an automated outbound
voice call to the organizer and event managers (not regular members) when
an incident is `CRITICAL`, reading the incident details via text-to-speech.

**Architecture:** A new transient `PendingVoiceCall` model (phone_number,
message, expiry) bridges outbound call placement to the inbound callback
Africa's Talking hits when the call is answered — the same problem
`ConferenceAccessCode` already solves for a different purpose. A new
`apps/voice_services/incident_calls.py` service resolves recipients and
dials via a thin `outbound_call_service.place_call` wrapper around the
already-installed `africastalking` SDK. The existing inbound callback view
(`apps/voice_services/views.py:voice_callback`) gains one new branch for
`direction == "Outbound"` calls, reusing its existing `voice_response()`
XML helper — today's public IVR logic is untouched. A new `APIView`,
mirroring `EventConferenceStartView`'s exact structure, exposes
`POST /api/voice/events/<event_id>/incidents/<incident_id>/call-team/`.

**Tech Stack:** Django 5 / DRF (existing `apps.voice_services`,
`apps.events`), the `africastalking` SDK (already in `requirements.txt`,
already used by `apps/sms/services/sms_service.py`), React 19 (existing
incident UI). No new dependencies.

See design spec: `docs/superpowers/specs/2026-09-25-team-voice-notifications-design.md` (Part 2).

**Scope note:** this plan was originally written backend-only, because at
the time `frontend/src/pages/IncidentManagement.jsx` didn't exist locally.
`origin/dev` has since gained it (incident list per event, with
organizer/manager status controls) — Task 6 below adds the "Call the team"
button to that real page.

**Deviations from the spec, decided while mapping it onto real files:**
- **Endpoint prefix:** the spec wrote `/api/events/<event_id>/incidents/<incident_id>/call-team/`. The actual convention for voice-triggered actions on an event (see `apps/voice_services/urls.py`'s `events/<int:event_id>/conference/...` routes, mounted at `/api/voice/`) is to live under `/api/voice/`. This plan uses `/api/voice/events/<event_id>/incidents/<incident_id>/call-team/` instead — same behavior, correct prefix.
- **Permission checks live in the view, not the service** — matching the sibling `MessageTeamView` from the Team SMS Messaging plan (404 for non-team callers, 403 for wrong role, both resolved directly in the view via `task_access_for_user`). The spec's `IncidentCallPermissionError` is dropped; `call_team_for_incident(incident)` no longer takes a `requested_by` argument, since by the time it's called the view has already confirmed the caller is organizer/manager. `IncidentCallStateError` (non-critical severity) stays in the service, matching how `conference_service.start_conference` raises `ConferenceStateError` internally.
- **The `VOICE_CRITICAL_CALLS_ENABLED` flag is checked in the view**, before calling the service — this exactly mirrors `EventConferenceStartView.post`, which checks `settings.VOICE_CONFERENCE_ENABLED` itself rather than delegating to `start_conference`.
- **Callback XML** reuses the existing `voice_response(message, finish=True)` helper instead of hand-building an XML string — it already exists, already escapes text safely via `xml.etree`, and produces exactly `<Say>...</Say><Hangup/>`.

## Global Constraints

- No new third-party dependency — `africastalking` is already installed and already used for SMS.
- `PendingVoiceCall` is transient routing state, not an audit log — no admin registration, no retention/cleanup job. A never-claimed row is simply ignored once `expires_at` passes.
- AT Voice callback field names used here (`direction`, `destinationNumber`) are taken from Africa's Talking's published outbound-call callback shape, but this codebase has never handled one before — Task 4 calls out where to double-check against a real sandbox call if the field names turn out to differ.
- Backend tests use Django's `TestCase` (service/callback layers) and DRF's `APITestCase` with `force_authenticate` (API layer), matching `apps/voice_services/test_conference_service.py` and `apps/voice_services/tests.py`. Mock `place_call` at `apps.voice_services.incident_calls.place_call` (where it's imported into).
- Run backend tests from `backend/`: `python manage.py test apps.voice_services`.
- Frontend has no test runner configured — the frontend task ends with a manual dev-server verification step.

---

### Task 1: `PendingVoiceCall` model

**Files:**
- Modify: `backend/apps/voice_services/models.py` (add model)
- Create: `backend/apps/voice_services/migrations/0003_pendingvoicecall.py` (generated, not hand-written)

**Interfaces:**
- Produces: `PendingVoiceCall(phone_number, message, created_at, expires_at)`

- [ ] **Step 1: Add the model**

Append to `backend/apps/voice_services/models.py`:

```python
class PendingVoiceCall(models.Model):
    """Transient routing state linking an outbound call to its message.

    Not an audit log: one row per outstanding call attempt, written when
    we dial and deleted when the matching outbound callback claims it.
    A row nobody ever answers is simply ignored once expires_at passes.
    """

    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["phone_number", "expires_at"]),
        ]

    def __str__(self):
        return f"Pending call to {self.phone_number}"
```

- [ ] **Step 2: Generate the migration**

Run: `cd backend && python manage.py makemigrations voice_services`
Expected: creates `apps/voice_services/migrations/0003_pendingvoicecall.py`.

- [ ] **Step 3: Apply and verify**

Run: `cd backend && python manage.py migrate voice_services`
Expected: applies cleanly with no errors.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/voice_services/models.py \
        backend/apps/voice_services/migrations/0003_pendingvoicecall.py
git commit -m "Add PendingVoiceCall routing-state model"
```

---

### Task 2: Outbound call placement + settings flag

**Files:**
- Create: `backend/apps/voice_services/outbound_call_service.py`
- Modify: `backend/config/settings.py` (add `VOICE_CRITICAL_CALLS_ENABLED`)
- Test: `backend/apps/voice_services/test_outbound_call_service.py` (new)

**Interfaces:**
- Produces: `place_call(phone_number)` — raises `VoiceCallError` on
  misconfiguration or provider failure, returns `None` on success.
- Produces: `VoiceCallError(Exception)`

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/voice_services/test_outbound_call_service.py`:

```python
"""Tests for outbound Africa's Talking voice call placement."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from .outbound_call_service import VoiceCallError, place_call


@override_settings(
    AFRICASTALKING_USERNAME="sandbox",
    AFRICASTALKING_API_KEY="test-key",
    AT_VOICE_NUMBER="+256711000000",
)
class PlaceCallTests(TestCase):
    @patch("apps.voice_services.outbound_call_service.africastalking")
    def test_places_call_with_configured_number(self, mock_sdk):
        place_call("+256700000001")

        mock_sdk.initialize.assert_called_once_with(
            "sandbox", "test-key",
        )
        mock_sdk.Voice.call.assert_called_once_with(
            "+256711000000", ["+256700000001"],
        )

    @patch("apps.voice_services.outbound_call_service.africastalking")
    def test_provider_error_raises_voice_call_error(self, mock_sdk):
        mock_sdk.Voice.call.side_effect = Exception("boom")

        with self.assertRaises(VoiceCallError):
            place_call("+256700000001")

    @override_settings(AT_VOICE_NUMBER="")
    def test_missing_configuration_raises_voice_call_error(self):
        with self.assertRaises(VoiceCallError):
            place_call("+256700000001")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.voice_services.test_outbound_call_service -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.voice_services.outbound_call_service'`

- [ ] **Step 3: Implement the service**

Create `backend/apps/voice_services/outbound_call_service.py`:

```python
"""Outbound Africa's Talking voice call placement for Tuviora."""

import africastalking
from django.conf import settings


class VoiceCallError(Exception):
    """Raised when an outbound voice call cannot be placed."""


def place_call(phone_number):
    """Place an outbound call from Tuviora's Africa's Talking voice number."""
    username = getattr(settings, "AFRICASTALKING_USERNAME", "")
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
    voice_number = getattr(settings, "AT_VOICE_NUMBER", "")

    if not all((username, api_key, voice_number)):
        raise VoiceCallError(
            "Africa's Talking Voice is not fully configured."
        )

    try:
        africastalking.initialize(username, api_key)
        africastalking.Voice.call(voice_number, [phone_number])
    except Exception as exc:
        raise VoiceCallError("Voice call request failed.") from exc
```

- [ ] **Step 4: Add the settings flag**

In `backend/config/settings.py`, immediately after the existing
`VOICE_CONFERENCE_MAX_PARTICIPANTS` block, add:

```python
# Critical-incident voice call escalation (organizer + managers only)
VOICE_CRITICAL_CALLS_ENABLED = (
    os.getenv("VOICE_CRITICAL_CALLS_ENABLED", "false").lower()
    == "true"
)
```

Add the matching line to `.env.example`, near the existing voice
conference settings:

```
VOICE_CRITICAL_CALLS_ENABLED=false
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.voice_services.test_outbound_call_service -v 2`
Expected: PASS — all 3 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/voice_services/outbound_call_service.py \
        backend/apps/voice_services/test_outbound_call_service.py \
        backend/config/settings.py \
        backend/.env.example
git commit -m "Add outbound voice call placement and its feature flag"
```

---

### Task 3: `call_team_for_incident` service

**Files:**
- Create: `backend/apps/voice_services/incident_calls.py`
- Test: `backend/apps/voice_services/test_incident_calls.py` (new)

**Interfaces:**
- Consumes: `place_call(phone_number)`, `VoiceCallError` from Task 2;
  `PendingVoiceCall` from Task 1; `apps.events.models.Event`,
  `Incident`, `EventMembership`; `apps.sms.models.SMSPreference`
- Produces: `call_team_for_incident(incident) -> {"dialed": int, "failed": int, "skipped": int}`, raises `IncidentCallStateError` for a non-critical incident.

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/voice_services/test_incident_calls.py`:

```python
"""Tests for critical-incident voice call escalation."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.events.models import Event, EventMembership, Incident
from apps.sms.models import SMSPreference

from .incident_calls import IncidentCallStateError, call_team_for_incident
from .models import PendingVoiceCall
from .outbound_call_service import VoiceCallError


class CallTeamForIncidentTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="incident_call_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="incident_call_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="incident_call_member",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Incident Call Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 10),
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
            phone_number="+256700000010",
            sms_enabled=False,
        )
        SMSPreference.objects.create(
            user=self.manager,
            phone_number="+256700000011",
            sms_enabled=False,
        )
        SMSPreference.objects.create(
            user=self.member,
            phone_number="+256700000012",
            sms_enabled=True,
        )

        self.incident = Incident.objects.create(
            event=self.event,
            title="Sound system failure",
            description="Main stage speakers are down.",
            category=Incident.Category.TECHNICAL,
            severity=Incident.Severity.CRITICAL,
        )

    def test_non_critical_incident_raises_state_error(self):
        self.incident.severity = Incident.Severity.HIGH
        self.incident.save(update_fields=["severity"])

        with self.assertRaises(IncidentCallStateError):
            call_team_for_incident(self.incident)

    @patch("apps.voice_services.incident_calls.place_call")
    def test_calls_organizer_and_managers_not_members(self, mock_place_call):
        call_team_for_incident(self.incident)

        called_numbers = {
            call.args[0] for call in mock_place_call.call_args_list
        }

        self.assertEqual(
            called_numbers,
            {"+256700000010", "+256700000011"},
        )

    @patch("apps.voice_services.incident_calls.place_call")
    def test_ignores_sms_enabled_flag(self, mock_place_call):
        # Both organizer and manager have sms_enabled=False above,
        # yet both must still be called.
        result = call_team_for_incident(self.incident)

        self.assertEqual(result["dialed"], 2)

    @patch("apps.voice_services.incident_calls.place_call")
    def test_recipient_without_phone_number_is_skipped(
        self, mock_place_call,
    ):
        SMSPreference.objects.filter(user=self.manager).delete()

        result = call_team_for_incident(self.incident)

        self.assertEqual(result["dialed"], 1)
        self.assertEqual(result["skipped"], 1)

    @patch("apps.voice_services.incident_calls.place_call")
    def test_creates_one_pending_call_row_per_dialed_recipient(
        self, mock_place_call,
    ):
        call_team_for_incident(self.incident)

        self.assertEqual(PendingVoiceCall.objects.count(), 2)
        pending_numbers = set(
            PendingVoiceCall.objects.values_list(
                "phone_number", flat=True,
            )
        )
        self.assertEqual(
            pending_numbers,
            {"+256700000010", "+256700000011"},
        )

    @patch("apps.voice_services.incident_calls.place_call")
    def test_provider_failure_is_counted_as_failed(self, mock_place_call):
        mock_place_call.side_effect = VoiceCallError("boom")

        result = call_team_for_incident(self.incident)

        self.assertEqual(result["dialed"], 0)
        self.assertEqual(result["failed"], 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.voice_services.test_incident_calls -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.voice_services.incident_calls'`

- [ ] **Step 3: Implement the service**

Create `backend/apps/voice_services/incident_calls.py`:

```python
"""Critical-incident voice call escalation, organizer/managers only."""

from datetime import timedelta

from django.utils import timezone

from apps.events.models import EventMembership, Incident
from apps.sms.models import SMSPreference

from .models import PendingVoiceCall
from .outbound_call_service import VoiceCallError, place_call

PENDING_CALL_LIFETIME = timedelta(minutes=10)


class IncidentCallStateError(Exception):
    """This incident is not eligible for a team call."""


def _build_message(incident):
    return (
        f"This is Tuviora. A critical incident has been reported "
        f"for {incident.event.name}. Category: "
        f"{incident.get_category_display()}. {incident.title}. "
        f"Please open the app for details."
    )


def call_team_for_incident(incident):
    """Call the organizer and event managers about a critical incident.

    Permission checking is the caller's responsibility (see
    IncidentCallTeamView) — by the time this runs, the requester has
    already been confirmed as the organizer or an event manager.
    """
    if incident.severity != Incident.Severity.CRITICAL:
        raise IncidentCallStateError(
            "Calls are only available for critical incidents."
        )

    recipient_ids = {incident.event.organizer_id}
    recipient_ids.update(
        EventMembership.objects.filter(
            event=incident.event,
            role=EventMembership.Role.MANAGER,
        ).values_list("user_id", flat=True)
    )

    # sms_enabled is deliberately not checked: a critical safety call
    # isn't gated by marketing SMS consent, only by having a number on file.
    phone_numbers = list(
        SMSPreference.objects.filter(user_id__in=recipient_ids)
        .exclude(phone_number="")
        .values_list("phone_number", flat=True)
    )

    message = _build_message(incident)
    dialed = 0
    failed = 0

    for phone_number in phone_numbers:
        PendingVoiceCall.objects.create(
            phone_number=phone_number,
            message=message,
            expires_at=timezone.now() + PENDING_CALL_LIFETIME,
        )
        try:
            place_call(phone_number)
            dialed += 1
        except VoiceCallError:
            failed += 1

    return {
        "dialed": dialed,
        "failed": failed,
        "skipped": len(recipient_ids) - len(phone_numbers),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.voice_services.test_incident_calls -v 2`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/voice_services/incident_calls.py \
        backend/apps/voice_services/test_incident_calls.py
git commit -m "Add call_team_for_incident escalation service"
```

---

### Task 4: Outbound branch in the voice callback

**Files:**
- Modify: `backend/apps/voice_services/views.py`
- Test: `backend/apps/voice_services/test_incident_call_callback.py` (new)

**Interfaces:**
- Consumes: `PendingVoiceCall` from Task 1, existing `voice_response()` helper (unmodified signature)

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/voice_services/test_incident_call_callback.py`:

```python
"""Tests for the outbound-call branch of the voice callback."""

from xml.etree import ElementTree

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import PendingVoiceCall


class OutboundCallbackTests(TestCase):
    def setUp(self):
        self.url = reverse("voice-callback")

    def spoken_text(self, response):
        root = ElementTree.fromstring(response.content)
        return " ".join(
            node.text or "" for node in root.iter("Say")
        )

    def test_speaks_and_deletes_matching_pending_call(self):
        PendingVoiceCall.objects.create(
            phone_number="+256700000099",
            message="This is Tuviora. A critical incident...",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        response = self.client.post(
            self.url,
            {
                "sessionId": "outbound-session-1",
                "direction": "Outbound",
                "destinationNumber": "+256700000099",
            },
        )

        self.assertIn(
            "This is Tuviora. A critical incident...",
            self.spoken_text(response),
        )
        self.assertEqual(PendingVoiceCall.objects.count(), 0)

    def test_expired_pending_call_is_not_spoken(self):
        PendingVoiceCall.objects.create(
            phone_number="+256700000098",
            message="Stale message",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            self.url,
            {
                "sessionId": "outbound-session-2",
                "direction": "Outbound",
                "destinationNumber": "+256700000098",
            },
        )

        self.assertNotIn("Stale message", self.spoken_text(response))

    def test_no_matching_pending_call_does_not_crash(self):
        response = self.client.post(
            self.url,
            {
                "sessionId": "outbound-session-3",
                "direction": "Outbound",
                "destinationNumber": "+256700000097",
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_inbound_calls_are_unaffected(self):
        response = self.client.post(
            self.url,
            {"sessionId": "inbound-session-1"},
        )

        self.assertIn(
            "Welcome to Tuviora",
            self.spoken_text(response),
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.voice_services.test_incident_call_callback -v 2`
Expected: FAIL on the first three tests (no outbound handling exists yet); the fourth passes already since inbound behavior is unmodified.

- [ ] **Step 3: Add the outbound branch**

In `backend/apps/voice_services/views.py`, add this import near the top,
alongside the existing ones:

```python
from django.utils import timezone

from .models import PendingVoiceCall
```

Then add this function above `voice_callback`:

```python
def _handle_outbound_callback(request):
    """Speak the message queued for this outbound call, then hang up.

    Africa's Talking's outbound-call callback payload is expected to
    include `destinationNumber` — verify this field name against a real
    sandbox call if it ever stops matching.
    """
    phone_number = request.POST.get("destinationNumber", "").strip()

    pending = (
        PendingVoiceCall.objects
        .filter(
            phone_number=phone_number,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )

    if pending is None:
        return voice_response("Goodbye.", finish=True)

    message = pending.message
    pending.delete()

    return voice_response(message, finish=True)
```

Then change the start of `voice_callback` from:

```python
@csrf_exempt
@require_POST
def voice_callback(request):
    """Handle incoming calls and subsequent keypad selections."""
    session_id = request.POST.get("sessionId", "").strip()
```

to:

```python
@csrf_exempt
@require_POST
def voice_callback(request):
    """Handle incoming calls and subsequent keypad selections."""
    if request.POST.get("direction", "") == "Outbound":
        return _handle_outbound_callback(request)

    session_id = request.POST.get("sessionId", "").strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.voice_services.test_incident_call_callback -v 2`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Run the full voice_services suite to check for regressions**

Run: `cd backend && python manage.py test apps.voice_services`
Expected: PASS — including every pre-existing conference and IVR test, unchanged.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/voice_services/views.py \
        backend/apps/voice_services/test_incident_call_callback.py
git commit -m "Handle outbound call callbacks for critical-incident announcements"
```

---

### Task 5: API endpoint

**Files:**
- Create: `backend/apps/voice_services/incident_call_views.py`
- Modify: `backend/apps/voice_services/urls.py`
- Test: `backend/apps/voice_services/test_incident_call_api.py` (new)

**Interfaces:**
- Consumes: `call_team_for_incident`, `IncidentCallStateError` from Task 3; `task_access_for_user` from `apps.events.views` (existing)
- Produces: `POST /api/voice/events/<event_id>/incidents/<incident_id>/call-team/`, URL name `event-incident-call-team`

- [ ] **Step 1: Write the failing API tests**

Create `backend/apps/voice_services/test_incident_call_api.py`:

```python
"""Tests for the critical-incident call-team endpoint."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventMembership, Incident


class IncidentCallTeamAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="call_api_organizer",
            password="TestPassword2026!",
        )
        self.manager = User.objects.create_user(
            username="call_api_manager",
            password="TestPassword2026!",
        )
        self.member = User.objects.create_user(
            username="call_api_member",
            password="TestPassword2026!",
        )
        self.outsider = User.objects.create_user(
            username="call_api_outsider",
            password="TestPassword2026!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Call API Test Event",
            category=Event.Category.CONFERENCE,
            date=date(2026, 10, 12),
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

        self.critical_incident = Incident.objects.create(
            event=self.event,
            title="Power outage",
            description="Main venue lost power.",
            category=Incident.Category.POWER,
            severity=Incident.Severity.CRITICAL,
        )
        self.medium_incident = Incident.objects.create(
            event=self.event,
            title="Late vendor",
            description="Catering is running late.",
            category=Incident.Category.OTHER,
            severity=Incident.Severity.MEDIUM,
        )

        self.url = reverse(
            "event-incident-call-team",
            kwargs={
                "event_id": self.event.id,
                "incident_id": self.critical_incident.id,
            },
        )

    def test_disabled_flag_returns_503(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    @patch("apps.voice_services.incident_call_views.call_team_for_incident")
    def test_organizer_can_call_team(self, mock_call):
        mock_call.return_value = {
            "dialed": 2, "failed": 0, "skipped": 0,
        }
        self.client.force_authenticate(self.organizer)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["dialed"], 2)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    @patch("apps.voice_services.incident_call_views.call_team_for_incident")
    def test_manager_can_call_team(self, mock_call):
        mock_call.return_value = {
            "dialed": 2, "failed": 0, "skipped": 0,
        }
        self.client.force_authenticate(self.manager)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    def test_member_gets_forbidden(self):
        self.client.force_authenticate(self.member)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    def test_outsider_gets_not_found(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(VOICE_CRITICAL_CALLS_ENABLED=True)
    def test_non_critical_incident_returns_400(self):
        url = reverse(
            "event-incident-call-team",
            kwargs={
                "event_id": self.event.id,
                "incident_id": self.medium_incident.id,
            },
        )
        self.client.force_authenticate(self.organizer)

        response = self.client.post(url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test apps.voice_services.test_incident_call_api -v 2`
Expected: FAIL — `NoReverseMatch: 'event-incident-call-team' not found`

- [ ] **Step 3: Add the view**

Create `backend/apps/voice_services/incident_call_views.py`:

```python
"""API for triggering critical-incident voice call escalation."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import EventMembership, Incident
from apps.events.views import task_access_for_user

from .incident_calls import IncidentCallStateError, call_team_for_incident


class IncidentCallTeamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id, incident_id):
        incident = get_object_or_404(
            Incident,
            pk=incident_id,
            event_id=event_id,
        )
        role = task_access_for_user(incident.event, request.user)

        if role is None:
            # Do not reveal private event/incident details to outsiders.
            raise Http404

        if role not in ("organizer", EventMembership.Role.MANAGER):
            return Response(
                {
                    "detail": (
                        "Only the organizer or event managers "
                        "can call the team."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not settings.VOICE_CRITICAL_CALLS_ENABLED:
            return Response(
                {"detail": "Critical incident calling is not enabled."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            result = call_team_for_incident(incident)
        except IncidentCallStateError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)
```

- [ ] **Step 4: Wire up the URL**

In `backend/apps/voice_services/urls.py`, add to the imports:

```python
from .incident_call_views import IncidentCallTeamView
```

and add this path alongside the other `events/<int:event_id>/conference/...` entries:

```python
    path(
        "events/<int:event_id>/incidents/<int:incident_id>/call-team/",
        IncidentCallTeamView.as_view(),
        name="event-incident-call-team",
    ),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python manage.py test apps.voice_services.test_incident_call_api -v 2`
Expected: PASS — all 6 tests.

- [ ] **Step 6: Run the full voice_services suite**

Run: `cd backend && python manage.py test apps.voice_services`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/voice_services/incident_call_views.py \
        backend/apps/voice_services/urls.py \
        backend/apps/voice_services/test_incident_call_api.py
git commit -m "Add critical-incident call-team API endpoint"
```

---

### Task 6: "Call the team" button on Incident Management

**Files:**
- Modify: `frontend/src/lib/team.js` (add `callTeamForIncident`)
- Modify: `frontend/src/pages/IncidentManagement.jsx` (organizer-facing incident list)
- Modify: `frontend/src/pages/TeamWorkspace.jsx` (manager-facing incident list)

**Interfaces:**
- Consumes: `POST /api/voice/events/<event_id>/incidents/<incident_id>/call-team/` from Task 5
- Produces: `callTeamForIncident(eventId, incidentId) -> Promise<{dialed, failed, skipped}>`

**Why two files:** `IncidentManagement.jsx` gets its event list from
`getEvents()`, which only returns events the current user organizes
(`EventListCreateView.get_queryset` filters `organizer=request.user`) — a
manager can't reach this page at all. The only place a manager currently
sees incidents is `TeamWorkspace.jsx`'s "Event incident reports" section,
which already gates its status-update buttons with
`selectedMembership?.role === 'manager'`. Since the whole point of this
feature is organizer **and** manager access, the button needs to go in
both places — putting it only in `IncidentManagement.jsx` would make it
practically organizer-only, contradicting the approved design.

- [ ] **Step 1: Add the API client function**

In `frontend/src/lib/team.js`, add:

```javascript
export function callTeamForIncident(eventId, incidentId) {
  return apiRequest(
    `/api/voice/events/${eventId}/incidents/${incidentId}/call-team/`,
    { method: 'POST' },
  )
}
```

- [ ] **Step 2: Add state, handler, and the button**

In `frontend/src/pages/IncidentManagement.jsx`, add to the top-of-file
imports:

```javascript
import { callTeamForIncident } from '../lib/team'
```

Add new state alongside the existing `useState` calls (after `refreshKey`):

```javascript
  const [callingId, setCallingId] = useState(null)
```

Add this handler alongside `updateStatus`:

```javascript
  async function handleCallTeam(incident) {
    if (callingId !== null) return

    setCallingId(incident.id)
    setError('')
    setNotice('')

    try {
      const result = await callTeamForIncident(eventId, incident.id)
      setNotice(
        `Called ${result.dialed} team member`
        + `${result.dialed === 1 ? '' : 's'}.`,
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setCallingId(null)
    }
  }
```

In the incident `<article>` block, immediately after the closing `</div>`
of the status-buttons row (the one mapping over `STATUSES`) and before the
closing `</article>`, add:

```jsx
              {incident.severity === 'critical' && (
                <div className="mt-3 border-t border-[#EDF0EA] pt-4">
                  <button
                    type="button"
                    disabled={callingId !== null}
                    onClick={() => handleCallTeam(incident)}
                    className="rounded-lg bg-[#B42318] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    {callingId === incident.id
                      ? 'Calling...'
                      : 'Call the team'}
                  </button>
                </div>
              )}
```

No client-side role check is added on this page — it has no existing
pattern for one (the organizer-only `EventTeamView` equivalent doesn't
gate its form client-side either), and the backend already enforces
organizer/manager via the 403 in `IncidentCallTeamView`. A click from a
disallowed role surfaces that 403's message through the existing
`catch (err) { setError(err.message) }` path.

- [ ] **Step 3: Add the same control to `TeamWorkspace.jsx`, manager-gated**

This page already restricts incident status updates to managers with
`{selectedMembership?.role === 'manager' && (...)}` — reuse that exact
gate for the call button, since organizers don't use this page at all
(it's driven by `user.team_memberships`, which is empty for an
organizer's own events).

Add to the top-of-file imports:

```javascript
import { callTeamForIncident } from '../lib/team'
```

Add new state alongside the existing incident-related `useState` calls:

```javascript
  const [callingIncidentId, setCallingIncidentId] = useState(null)
```

Add this handler alongside `updateIncidentStatus`:

```javascript
  async function handleCallTeam(incident) {
    if (callingIncidentId !== null) return

    setCallingIncidentId(incident.id)
    setError('')
    setNotice('')

    try {
      const result = await callTeamForIncident(
        selectedEventId,
        incident.id,
      )
      setNotice(
        `Called ${result.dialed} team member`
        + `${result.dialed === 1 ? '' : 's'}.`,
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setCallingIncidentId(null)
    }
  }
```

Inside the `{selectedMembership?.role === 'manager' && (...)}` block, add
the button after the closing `</div>` of the status-buttons row it
already renders (`.map(([value, label]) => ...)`), still inside that same
conditional, only when the incident is critical:

```jsx
                      {incident.severity === 'critical' && (
                        <div className="mt-3">
                          <button
                            type="button"
                            disabled={callingIncidentId !== null}
                            onClick={() => handleCallTeam(incident)}
                            className="rounded-lg bg-[#B42318] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                          >
                            {callingIncidentId === incident.id
                              ? 'Calling...'
                              : 'Call the team'}
                          </button>
                        </div>
                      )}
```

- [ ] **Step 4: Manually verify in the browser**

Sign in as an organizer with an event that has a `critical`-severity
incident, open Incident Management, and confirm the button appears only
on that incident's card. Then sign in as a manager on the same event via
the team workspace, and confirm the button appears there too, on the same
incident, gated correctly (a `member`-role account should not see it at
all, matching the existing status-button gating).

With `VOICE_CRITICAL_CALLS_ENABLED=false` (the local default), click it
from either page and confirm the 503's message ("Critical incident
calling is not enabled.") surfaces in the error banner. Set
`VOICE_CRITICAL_CALLS_ENABLED=true`, restart the backend, click again,
and confirm a notice banner shows a dialed count (it will be 0 without
real Africa's Talking credentials and a phone number on file — confirm
that shows as `dialed: 0` in the notice, not a crash or 500).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/team.js \
        frontend/src/pages/IncidentManagement.jsx \
        frontend/src/pages/TeamWorkspace.jsx
git commit -m "Add Call the team button for critical incidents"
```
