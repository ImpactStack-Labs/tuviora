# Team SMS Messaging & Critical-Incident Voice Calls — Design

**Goal:** Give organizers and managers two audience-scoped communication
channels that don't exist yet: a free-text SMS to the whole event team,
and an escalation-only automated voice call to the organizer and
managers when an incident is marked `CRITICAL`.

**Non-goals:** No persisted message/call history or audit log (SMS
already has none; this stays consistent). No multilingual voice
content — the announcement is English only, matching the fixed
templates elsewhere in this codebase, not the caller-selected
language menu the public IVR uses. No automatic triggering of calls —
every call is a deliberate button press by a human, never a signal
handler on `Incident` save. No changes to attendee-facing SMS
behavior beyond a rename.

## Current state (context)

- `apps/sms/services/event_sms_notifications.py` has one function,
  `send_event_sms(user_ids, message)`, used only by
  `apps/events/payment_views.py` to confirm a single attendee's
  payment. There is no team-messaging call site today.
- `apps/events/views.py:task_access_for_user(event, user)` already
  returns `"organizer"`, `"manager"`, `"member"`, or `None` and is
  reused by the voice conference feature
  (`apps/voice_services/conference.py`) for its own permission
  checks. Both new features reuse this helper — no new permission
  logic.
- `apps/events/models.py:Incident` already has `severity`
  (`low/medium/high/critical`), `category`, `status`, and `event`.
  Nothing currently reacts to an incident's severity.
- `apps/voice_services/` is inbound-only today: a public multilingual
  IVR menu (`/api/voice/callback/`) and a private conference callback
  (`/api/voice/conference/callback/`) that currently rejects all
  requests because incoming Africa's Talking callback authentication
  isn't built yet. No outbound call has ever been placed by this
  codebase.
- The `africastalking` SDK (already in `requirements.txt`) exposes
  `Voice.call(callFrom, callTo, callback=None)` — the AT `/call`
  request body is only `username`/`from`/`to`. There is no per-call
  webhook URL parameter.

## Part 1: Team SMS messaging

### Service layer

`apps/sms/services/event_sms_notifications.py`:

- Rename the existing function body to a private helper,
  `_send_sms_to_users(user_ids, message)` — logic unchanged.
- Add `send_team_sms(event, message)`: resolves recipients as
  `event.organizer_id` plus every `EventMembership.objects.filter(event=event)`
  user, dedupes, and calls the private helper.
- Add `send_attendee_sms(user_ids, message)`: a thin public wrapper
  around the private helper, functionally identical to today's
  `send_event_sms`. Update the one existing call site in
  `payment_views.py` to use it.

Both public functions keep the same return shape:
`{"submitted": int, "failed": int, "skipped": int}`.

### API

`POST /api/events/<event_id>/team/message/`

- DRF `APIView`, `IsAuthenticated`, following the
  `ConferenceEventMixin` pattern in
  `apps/voice_services/conference_views.py`.
- 404 (via `Http404`, not a 403, to avoid revealing the event exists
  to non-team users) if `task_access_for_user(event, user) is None`.
- 403 if the caller's role is `"member"` (only `organizer`/`manager`
  may send).
- 400 if `message` is missing/blank.
- 200 with `send_team_sms(event, message)`'s result on success.

### Frontend

One "Message team" text box + send button on the organizer's existing
team page, visible only to organizer/manager. No new page or route.

## Part 2: Critical-incident voice call

### The routing problem

Africa's Talking calls back to a single, account-configured
`AT_VOICE_CALLBACK_URL` for **every** call event on a voice number —
inbound or outbound-initiated — and outbound call requests carry no
callback-URL parameter of their own. When a team member answers our
outbound call, AT's callback POST tells us the call is `Outbound` and
which number was reached, but nothing about *why* we called them,
since AT's `sessionId` isn't known until the call connects.

This is the same class of problem the private conference feature has
already solved once for a different purpose: `ConferenceAccessCode`
binds a short-lived PIN to a caller's session so a stateless callback
can look up what to do. We reuse that pattern rather than invent a
new one.

### New model: `PendingVoiceCall`

`apps/voice_services/models.py`:

```python
class PendingVoiceCall(models.Model):
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
```

Not an audit log — purely transient routing state, one row per
outstanding call attempt. Written when we dial, read and deleted when
the matching outbound callback arrives. A stale, never-answered row
is simply ignored once `expires_at` passes (checked at lookup time;
no separate cleanup job — volume here is inherently tiny, one row per
recipient per critical incident).

### Service: `apps/voice_services/incident_calls.py`

`call_team_for_incident(incident, requested_by)`:

1. `task_access_for_user(incident.event, requested_by)` must be
   `"organizer"` or `"manager"` — else raise
   `IncidentCallPermissionError`.
2. `incident.severity` must equal
   `Incident.Severity.CRITICAL` — else raise `IncidentCallStateError`.
3. `settings.VOICE_CRITICAL_CALLS_ENABLED` must be `True` — else raise
   `VoiceCallError` (mirrors `SMSServiceError`'s "disabled" message).
4. Recipients: `incident.event.organizer` plus
   `EventMembership.objects.filter(event=incident.event, role=EventMembership.Role.MANAGER)`.
   Regular `member`-role team members are not called (SMS already
   reaches them via Part 1).
5. For each recipient, look up their phone number via
   `SMSPreference` (matched on `user_id`, non-empty `phone_number`;
   `sms_enabled` is **not** checked — a critical safety call isn't
   gated by marketing SMS consent). No phone number on file → counted
   as `skipped`.
6. For each phone number: build the spoken message (event name,
   incident category, title — see template below), create a
   `PendingVoiceCall` row (10-minute expiry, matching the existing
   `ConferenceAccessCode` lifetime convention), then call
   `africastalking.Voice.call(callFrom=settings.AT_VOICE_NUMBER, callTo=[phone_number])`.
7. Return `{"dialed": int, "failed": int, "skipped": int}`.

Spoken template: `"This is Tuviora. A critical incident has been
reported for {event.name}. Category: {incident.get_category_display()}.
{incident.title}. Please open the app for details."`

### Callback dispatcher change

The existing inbound voice callback view gains one new branch, added
before today's IVR logic runs:

```python
if request.POST.get("direction") == "Outbound":
    pending = (
        PendingVoiceCall.objects
        .filter(
            phone_number=request.POST.get("destinationNumber", ""),
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
    if pending is not None:
        pending.delete()
        return HttpResponse(
            f"<Response><Say>{escape(pending.message)}</Say></Response>",
            content_type="application/xml",
        )
    # No match: fall through to a safe hang-up, not the IVR menu.
```

Everything else (no `direction=Outbound`, or no matching pending row)
falls through to today's behavior unchanged. The exact AT field names
(`direction`, `destinationNumber`) are per Africa's Talking's
published Voice callback payload — worth a quick confirmation against
their current docs during implementation, since this codebase has
never handled an outbound callback before and this spec's names could
be slightly stale.

### API

`POST /api/events/<event_id>/incidents/<incident_id>/call-team/`

- Same `ConferenceEventMixin`-style 404 for non-team callers.
- 403 `IncidentCallPermissionError` → "Only the organizer or event
  managers can call the team."
- 400 `IncidentCallStateError` → "Calls are only available for
  critical incidents."
- 503 if `VOICE_CRITICAL_CALLS_ENABLED` is false → "Critical incident
  calling is not enabled." (mirrors `EventConferenceStartView`'s
  503 for `VOICE_CONFERENCE_ENABLED`).
- 200 with `call_team_for_incident(...)`'s result on success.

### Settings

`VOICE_CRITICAL_CALLS_ENABLED` (default `false`), read the same way
`VOICE_CONFERENCE_ENABLED` is. Deliberately a **separate** flag from
conference calling: this feature doesn't share the conference
feature's unresolved inbound-callback-authentication risk (there's no
caller-supplied PIN or room access here, just a one-way announcement),
so it shouldn't be blocked on that work finishing. It does still share
the same AT phone number and the same unauthenticated callback
endpoint, which is a real if lower-severity exposure: an attacker who
knows a team member's phone number and can time a spoofed "Outbound
answered" callback could fish for that number's pending incident
message. Acceptable for a v1 escalation tool where the leaked content
is an incident category and title, not credentials — but worth
revisiting if callback authentication work happens for the conference
feature, since the fix would cover both.

### Frontend

A "Call the team" button on an incident's detail view, rendered only
when `severity === "critical"` and the viewer is organizer/manager.

## Testing

- `apps/sms/test_team_sms.py`: `send_team_sms` recipient resolution;
  endpoint 404 (non-team) / 403 (`member` role) / 200 (organizer,
  manager) with correct counts.
- `apps/voice_services/test_incident_calls.py` (same `TestCase` +
  mocked-`africastalking` style as `test_conference_service.py`):
  permission rejection, non-critical severity rejection, disabled-flag
  rejection, phone-number-missing recipients counted as skipped,
  `PendingVoiceCall` created per dialed recipient.
- `apps/voice_services/test_incident_call_callback.py`: the outbound
  branch returns the right `<Say>` XML for a matching pending row and
  deletes it; falls through to existing IVR behavior untouched when
  `direction != "Outbound"` or there's no match.
- No live Africa's Talking end-to-end test — same limitation the
  conference feature already has.

Run: `cd backend && python manage.py test apps.sms apps.voice_services`.
