# Tuviora Voice Services

Tuviora's voice services include a multilingual public event-information
menu, critical-incident calls to event leads and a private event
conference feature.

## Multilingual voice menu

`POST /api/voice/callback/` offers English, Kiswahili and Luganda, then
a menu for event information, venue directions and registration
assistance. Speech is generated with Sunbird AI text-to-speech
(`sunbird.py`, requires `SUNBIRD_API_KEY`).

## Critical-incident calls

`POST /api/voice/events/<event_id>/incidents/<incident_id>/call-team/`
lets the organizer or an event manager place automated voice calls about
a **critical** incident to the organizer and all accepted managers who
have a saved phone number. SMS consent is not required for these safety
calls. The endpoint returns `503` unless
`VOICE_CRITICAL_CALLS_ENABLED=true`, and it requires `AT_VOICE_NUMBER` and
Africa's Talking credentials.

## Private conferences

### Current development status

The conference backend is merged into `dev` but not yet usable end to end.
It has automated tests for conference permissions, lifecycle operations,
one-time access codes, caller sessions, rate limiting, provider commands
and the private callback's fail-closed behavior.

The private conference callback currently rejects all requests.
Incoming Africa's Talking callback authentication has not yet been
established. Live conference calling is not ready.

Keep `VOICE_CONFERENCE_ENABLED=false` until the required security and
end-to-end integration work is complete.

### Permissions

- Organizer: start and end their event's conference, obtain an access
  code and join.
- Accepted event managers and members: obtain an access code and join.
- Attendees, pending invitees and unrelated users: no conference access.

Conference permissions use the event membership system. Membership is
checked again when a verified caller attempts to access a conference.

### Conference lifecycle

A conference starts in the ready state, becomes active when its organizer
starts it, and becomes ended when the organizer terminates it.

Ended conferences cannot be restarted. Conference room names are
randomly generated and are not exposed by the public status API.

When the conference feature is enabled, ending an active conference
requests termination through Africa's Talking before updating the
database. Provider errors leave the database conference active, but
the actual remote state may require reconciliation.

## API endpoints

All event conference management endpoints require authentication.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/voice/events/<event_id>/conference/` | View conference status |
| POST | `/api/voice/events/<event_id>/conference/start/` | Organizer starts conference |
| POST | `/api/voice/events/<event_id>/conference/end/` | Organizer ends conference |
| POST | `/api/voice/events/<event_id>/conference/access-code/` | Eligible member requests a one-time code |
| POST | `/api/voice/conference/callback/` | Private callback; currently rejects all requests |
| POST | `/api/voice/events/<event_id>/incidents/<incident_id>/call-team/` | Critical-incident call (see above) |

The existing public multilingual voice menu remains at
`/api/voice/callback/` and is separate from the conference callback.

### Access codes and caller sessions

Eligible members can request an eight-digit, one-time access code.
Codes expire after ten minutes and are stored as keyed hashes.

A redeemed code is bound to a specific telephone call session and
caller number for up to fifteen minutes. Rate limiting restricts
repeated unsuccessful PIN attempts.

These safeguards depend on authenticating the telephone provider's
incoming callback before processing caller-supplied information.

## Local setup

From the repository root, install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Copy the repository's `.env.example` to `backend/.env` and
configure the required application settings. Never commit `.env`
or real credentials.

Apply migrations:

```bash
python backend/manage.py migrate
```

Run Django's configuration checks:

```bash
python backend/manage.py check
```

Run the voice-service tests:

```bash
cd backend
python manage.py test apps.voice_services
```

## Environment configuration

- `AT_VOICE_NUMBER`: Africa's Talking voice number.
- `AT_VOICE_CALLBACK_URL`: configured voice callback URL.
- `VOICE_CONFERENCE_ENABLED`: keep `false` until live integration is ready.
- `VOICE_CONFERENCE_MAX_PARTICIPANTS`: conference participant limit.
- `VOICE_CRITICAL_CALLS_ENABLED`: enables critical-incident calls.
- `SUNBIRD_API_KEY`: Sunbird AI text-to-speech for the voice menu.
- `REDIS_URL`: shared Redis connection for multi-instance session state
  and rate limiting.

Voice uses `AT_VOICE_USERNAME` and `AT_VOICE_API_KEY`, falling back to
`AFRICASTALKING_USERNAME` and `AFRICASTALKING_API_KEY` when blank. Set
them to run voice on a different Africa's Talking app than SMS/USSD
(e.g. live voice, sandbox SMS). Do not include credentials
in callback URLs.

A shared Redis cache and configured voice number are required by
the conference system checks when the feature is enabled.

## Remaining work

1. Confirm and implement authentication for incoming Africa's Talking
   voice callbacks.
2. Implement the authenticated conference PIN-entry call flow.
3. Connect verified callers to the correct conference room.
4. Complete provider event handling and remote-state reconciliation.
5. Build organizer and team-member frontend controls.
6. Configure shared Redis and perform controlled end-to-end tests.

Do not enable live conference calling solely because automated tests pass.
