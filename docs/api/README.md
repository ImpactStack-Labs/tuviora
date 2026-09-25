# API Reference

All endpoints are served by Django under `/api/`. The frontend reaches them
through the Vite dev proxy (see [frontend README](../../frontend/README.md)).

## Conventions

- **Authentication:** Django session cookies. Call `GET /api/auth/csrf/`
  first, then send the `csrftoken` cookie value as `X-CSRFToken` on every
  `POST`, `PATCH`, `PUT` and `DELETE`.
- Unless marked **public**, endpoints require a signed-in user.
- **Roles are per event:** the event's *organizer* (its creator), and
  accepted team members with the **manager** or **member** role.
- Errors return `{"detail": "..."}`. When a user has no connection to a
  private event, the API returns `404` rather than `403`, so it does not
  reveal that the event exists.
- The backend always sets the owner fields (`organizer`, `reported_by`,
  `attendee`) from the signed-in user. Clients must not send them.

## Auth and accounts

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/health/` | public | Health check |
| GET | `/api/auth/csrf/` | public | Set the CSRF cookie |
| POST | `/api/auth/register/` | public | Create an account and send a verification email; optional phone number and SMS opt-in (`sms_enabled`) |
| POST | `/api/auth/verify-email/` | public | Verify an email address with the token from the verification link |
| POST | `/api/auth/login/` | public | Sign in (username and password) |
| POST | `/api/auth/logout/` | signed in | Sign out |
| GET | `/api/auth/me/` | signed in | Current user, including organizer status and team memberships |

## Events

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/events/` | signed in | Events you organize |
| GET | `/api/events/?scope=lead` | signed in | Events you organize or manage (used by the Communications, Feedback, Payments, Analytics and Budget pages) |
| POST | `/api/events/` | signed in | Create an event (starts as `draft`) |
| POST | `/api/events/<event_id>/publish/` | organizer | Publish a draft event |
| GET | `/api/events/public/` | public | Published events whose date has not passed |
| GET | `/api/events/public/<id>/` | public | One published, upcoming event |

Event statuses: `draft`, `published`, `cancelled`, `completed`.
Formats: `physical`, `virtual`, `hybrid`.

Example event object:

```json
{
  "id": 1,
  "name": "Tuviora Hackathon",
  "category": "hackathon",
  "description": "An event operations hackathon.",
  "date": "2026-10-01",
  "timezone_name": "Africa/Kampala",
  "start_time": "09:00:00",
  "end_time": "17:00:00",
  "event_format": "physical",
  "venue": "Uganda Christian University",
  "landmark": "Mukono",
  "latitude": "0.353600",
  "longitude": "32.755300",
  "online_platform": "",
  "online_url": "",
  "joining_instructions": "",
  "capacity": 100,
  "organizer": 1,
  "status": "draft",
  "created_at": "2026-09-23T10:00:00Z",
  "updated_at": "2026-09-23T10:00:00Z"
}
```

`id`, `organizer`, `status`, `created_at` and `updated_at` are read-only.

## Ticket types

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET, POST | `/api/events/<event_id>/ticket-types/` | organizer | List or create ticket types (`name`, `price`, `currency`, `is_active`) |
| GET, PUT, PATCH, DELETE | `/api/events/<event_id>/ticket-types/<id>/` | organizer | Manage one ticket type |

Supported currencies: UGX, KES, RWF, CDF, USD, ZMW.

## Registrations, tickets and payments

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/events/<event_id>/registrations/` | organizer | All registrations for the event |
| POST | `/api/events/<event_id>/registrations/` | signed in | Register (choose a ticket type if the event has any) |
| GET | `/api/events/<event_id>/registrations/me/` | signed in | Your registration for this event |
| POST | `/api/events/<event_id>/registrations/me/cancel/` | signed in | Cancel your registration |
| GET | `/api/events/registrations/me/` | signed in | All your registrations |
| GET | `/api/events/<event_id>/registrations/me/ticket/` | signed in | Issue or fetch your ticket (confirmed registrations only) |
| POST | `/api/events/<event_id>/registrations/me/pay/` | signed in | Start a MarzPay payment. Body: `method` (`mobile_money` or `card`), plus `phone_number` for Mobile Money |
| POST | `/api/payments/marzpay/webhook/` | MarzPay, signed with HMAC | Payment result; confirms the registration on `collection.completed` |
| POST | `/api/events/<event_id>/tickets/check-in/` | organizer or team | Check in with `{"token": "<uuid>"}` (QR token or ticket reference) |

Registration statuses: `payment_pending` → `confirmed`, or `cancelled`.
Free registrations are confirmed immediately. Registering returns `409`
when the user is already registered or the event is full. Check-in returns
`409` when the ticket has already been used and `403` when the registration
is not confirmed. See [Payments](../payments/README.md).

## Budget, payments and analytics

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET, POST | `/api/events/<event_id>/budget/` | organizer or manager | Budget lines: `category`, `description`, `vendor`, `planned_amount`, `actual_amount`, `paid` |
| GET, PUT, PATCH, DELETE | `/api/events/<event_id>/budget/<id>/` | organizer or manager | Manage one line |
| GET | `/api/events/<event_id>/summary/` | organizer or manager | Registrations (by status, day, ticket type), attendance and check-in rate, payments collected and pending, budget planned/actual/unpaid/net, average rating |
| GET | `/api/events/<event_id>/payments/` | organizer | Payment list with attendee, amount, method and status |

Budget categories: venue, catering, equipment, marketing, transport, staff, other. Net = payments collected − actual spend.

## Team

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/events/<event_id>/team/` | organizer or team | Team roster |
| GET, POST | `/api/events/<event_id>/invitations/` | organizer | List invitations, or invite by email with a `manager` or `member` role |
| POST | `/api/events/<event_id>/invitations/<invitation_id>/revoke/` | organizer | Revoke a pending invitation |
| POST | `/api/events/invitations/accept/` | signed in (the invitee) | Accept using the invitation token |
| POST | `/api/events/<event_id>/team/message/` | organizer or manager | SMS the organizer and all accepted members: `{"message": "..."}` |

## Announcements

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET, POST | `/api/events/<event_id>/announcements/` | organizer or manager | Announcement history, or SMS `{"message": "..."}` (1–480 chars) to confirmed, opted-in attendees |

`python manage.py send_event_reminders` texts confirmed attendees of events happening tomorrow; run it daily from cron. Running it twice on the same day sends once.

## Readiness tasks

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/events/<event_id>/tasks/` | organizer or team | Organizers and managers see all tasks; members see only their own |
| POST | `/api/events/<event_id>/tasks/` | organizer | Create and assign a task (notifies the assignee) |
| GET, PUT, PATCH | `/api/events/<event_id>/tasks/<id>/` | organizer or team | Non-organizers may only `PATCH` `{"status": ...}` |

Task statuses: `pending`, `in_progress`, `completed`.

## Incidents

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET, POST | `/api/events/<event_id>/incidents/` | organizer or team | List incidents, or report one (created as `open`) |
| GET, PATCH | `/api/events/<event_id>/incidents/<id>/` | read: organizer or team. Update: organizer or manager | View or update an incident |
| POST | `/api/voice/events/<event_id>/incidents/<incident_id>/call-team/` | organizer or manager | Voice-call the organizer and managers about a **critical** incident. Returns `503` unless `VOICE_CRITICAL_CALLS_ENABLED=true` |

Categories: network, power, venue, security, attendance, payment,
technical, other. Severities: low, medium, high, critical.
Statuses: open, in_progress, resolved, closed.

## AI (OpenAI)

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/events/incidents/<incident_id>/ai-analysis/` | organizer | Generate or refresh an analysis: classification, suggested severity, priority, recommended actions and a draft message |
| GET | `/api/events/incidents/<incident_id>/ai-analysis/detail/` | organizer | Fetch the stored analysis |
| POST | `/api/events/incidents/<incident_id>/ai-analysis/approve/` | organizer | Approve a pending recommendation |
| GET | `/api/events/<event_id>/feedback/` | organizer or manager | List attendee feedback |
| POST | `/api/events/<event_id>/feedback/` | confirmed attendee | Submit or update your feedback: `rating` (1–5) and/or `comment`. `201` created, `200` updated |
| GET | `/api/events/<event_id>/feedback/me/` | signed in | Your own feedback for the event (`404` if none) |
| GET, POST | `/api/events/<event_id>/feedback/analysis/` | organizer or manager | Fetch, or generate, an AI summary of the feedback |

When `OPENAI_API_KEY` is missing or the provider fails, the AI endpoints
return `503`.

## USSD and voice

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/ussd/callback/` | Africa's Talking USSD callback. See [USSD sandbox](../ussd-sandbox.md) |
| POST | `/api/voice/callback/` | Public multilingual voice menu |
| GET | `/api/voice/events/<event_id>/conference/` | Conference status |
| POST | `/api/voice/events/<event_id>/conference/start/` and `.../end/` | Organizer starts or ends the conference |
| POST | `/api/voice/events/<event_id>/conference/access-code/` | One-time conference access code |
| POST | `/api/voice/conference/callback/` | Private conference callback (currently rejects all requests) |

Conference details: [Voice Services](../../backend/apps/voice_services/README.md).
