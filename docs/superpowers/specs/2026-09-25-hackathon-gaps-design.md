# Hackathon Focus-Area Gaps — Design

**Date:** 2026-09-25
**Status:** Approved in brainstorming; awaiting spec review

Closes the gaps found when Tuviora was compared with the Africa's Talking
hackathon focus areas: attendee communication (area 2), budgeting and
payments (3), attendee feedback and analytics (5, 6), and USSD registration
(1, 7).

Four features, built in this order. Each is independently shippable.

1. SMS announcements and reminders
2. Attendee feedback over the web and USSD, plus an organizer Feedback page
3. Payments, Analytics and Budget pages
4. USSD registration for free events

## Shared conventions

- **Roles:** "organizer" is `Event.organizer`. "Manager" and "member" are
  accepted `EventMembership` roles. Role lookup reuses
  `apps.events.views.task_access_for_user`.
- **Hiding private events:** a user with no connection to an event gets
  `404`. A connected user without the required role gets `403`.
- **SMS:** always sent through the existing consent-aware services
  (`send_attendee_sms`, `send_sms`). When `SMS_ENABLED` is false, sends are
  counted as failed rather than raising errors.
- **Frontend:** every new organizer page follows the `EventTeam.jsx`
  pattern: an event picker from `getEvents()`, API helpers in `src/lib/*.js`
  built on `apiRequest`, and `formatApiError` for error messages. Each new
  page replaces an `OrganizerModule` placeholder route in `OrganizerLayout`.
- **Tests:** follow the existing `APITestCase` style, with Africa's Talking
  and OpenAI mocked.
- **Docs:** each feature updates `docs/api/README.md`, the root README
  feature list, and `docs/ussd-sandbox.md` or `docs/sms-integration.md`
  where relevant.

---

## 1. SMS announcements and reminders

### Model

`EventAnnouncement` (app `events`)

| Field | Type |
| --- | --- |
| event | FK Event, `related_name="announcements"` |
| sent_by | FK User, nullable (null means an automatic reminder) |
| message | TextField |
| submitted, failed, skipped | PositiveIntegerField |
| created_at | auto_now_add |

Ordered newest first.

### API

`/api/events/<event_id>/announcements/`, available to the organizer and
managers.

- `GET` returns the event's announcements.
- `POST {"message": "..."}`:
  - The message must be 1–480 characters after trimming; otherwise `400`.
  - Recipients are the user IDs of the event's registrations with status
    `confirmed`.
  - It calls `send_attendee_sms(user_ids, message)`, stores an
    `EventAnnouncement` with the returned counts, and responds `201` with
    the stored announcement.

### Reminder command

`python manage.py send_event_reminders`

- Selects published events whose `date` is tomorrow (local date).
- Skips any event that already has an announcement with `sent_by=None`
  created today, so running it twice sends only once.
- Message: `Reminder: {name} is tomorrow, {date:%d %b} at {start_time:%H:%M}, {venue or "online"}.`
- Sends to confirmed attendees through the same path as the `POST` above.
- Prints a per-event summary.
- In deployment it is run daily from cron (documented, not provisioned).

### Frontend

The **Communications** placeholder becomes `Communications.jsx`:

- Event picker.
- Message textarea with a character count and an SMS segment count
  (segments of 160 characters, or 153 each once the message exceeds 160).
- **Insert reminder** button, which fills in the reminder template from the
  selected event.
- **Send** button, followed by a notice such as "Sent to N · M skipped (no
  SMS consent or phone) · K failed".
- History list showing date, sender ("Automatic reminder" when null),
  message and counts.

Helpers go in `src/lib/announcements.js`.

### Tests

- Permissions: organizer and manager get `201`; member gets `403`;
  outsider gets `404`.
- Only confirmed registrations are passed as recipients; cancelled and
  payment-pending are not.
- Empty or over-length messages are rejected.
- History is scoped to the event.
- The command sends once for tomorrow's events and a second run is a no-op.

---

## 2. Attendee feedback (web and USSD) and organizer Feedback page

### Tighter permissions on the existing API (security fix)

`/api/events/<event_id>/feedback/`

- `POST` is allowed only for users with a **confirmed** registration for
  the event; others get `403`. It is an upsert: one `Feedback` per
  (event, attendee), and resubmitting updates the existing entry
  (`update_or_create`, returning `200` on update and `201` on create).
- `GET` is limited to the organizer and managers (`404` or `403` for
  others, per the shared conventions).
- Validation: `rating` is 1–5 or null. At least one of `rating` or a
  non-blank `comment` is required.

New: `GET /api/events/<event_id>/feedback/me/` returns the caller's own
feedback for the event, or `404`.

The model change is `Feedback.comment` → `TextField(blank=True)`, which
needs one migration.

The four existing feedback tests in `apps/events/tests.py` are updated to
give the test user a confirmed registration first. The existing
`/feedback/analysis/` endpoints are unchanged.

### USSD

New main-menu option **5. Rate an event**:

1. `CON Enter the event ID:`
2. Look up the registration with `get_registration(event_id, phone)`. If
   there is none or it isn't confirmed, reply
   `END No registration found for this event.` (the same generic message
   as option 2).
3. `CON Rate {name} from 1 (poor) to 5 (excellent):`. Anything other than
   1–5 gets `END Invalid rating. Please dial again.`
4. `CON Add a comment, or enter 9 to skip:`
5. Save through the same upsert as the web, with a comment of `""` when the
   caller skips. Reply `END Thank you for your feedback.`

Africa's Talking sends input as cumulative `*`-separated text. A comment
containing `*` is rejoined from the remaining parts. The existing 160-character
`text` limit still applies.

### Frontend

- **My Registrations:** on each confirmed registration, a **Rate this
  event** section with a 1–5 rating and a comment, pre-filled from
  `feedback/me/`.
- The **Feedback** placeholder becomes `FeedbackPage.jsx`:
  - Event picker.
  - Average rating, response count and a 1–5 breakdown bar.
  - Comment list.
  - **Generate AI summary** button (`POST /feedback/analysis/`) that shows
    themes, concerns and suggested improvements. If `503` is returned, it
    shows "AI summary unavailable — OPENAI_API_KEY not configured."
  - Any existing analysis is loaded on open (`GET`; a `404` means none
    yet).

Helpers go in `src/lib/feedback.js`.

### Tests

- Submit: a confirmed attendee gets `201`, then `200` on resubmit with a
  single row. A non-registered or payment-pending user gets `403`.
- List: organizer and manager are allowed; member gets `403`; outsider
  gets `404`.
- `feedback/me/`.
- USSD: happy path with a comment; skipping with 9; invalid rating;
  unknown phone gets the generic reply; a comment containing `*`.

---

## 3. Payments, Analytics and Budget pages

### Model

`BudgetItem` (app `events`)

| Field | Type |
| --- | --- |
| event | FK Event, `related_name="budget_items"` |
| category | choices: venue, catering, equipment, marketing, transport, staff, other |
| description | CharField(200) |
| vendor | CharField(120), blank |
| planned_amount | Decimal(12,2) |
| actual_amount | Decimal(12,2), nullable |
| paid | Boolean, default False |
| created_by | FK User, nullable |
| created_at, updated_at | timestamps |

Amounts use the event's currency: the currency of its first active ticket
type, otherwise `UGX`. The currency is not stored per item.

### API (organizer and managers unless noted)

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET, POST | `/api/events/<id>/budget/` | List or add budget lines |
| PATCH, DELETE | `/api/events/<id>/budget/<item_id>/` | Edit or remove a line |
| GET | `/api/events/<id>/summary/` | Aggregates for the dashboards |
| GET | `/api/events/<id>/payments/` | Payment list, **organizer only** |

`summary` response:

```json
{
  "currency": "UGX",
  "registrations": {"confirmed": 0, "payment_pending": 0, "cancelled": 0,
                     "by_day": [{"date": "2026-09-20", "count": 3}],
                     "by_ticket_type": [{"name": "VIP", "count": 2}]},
  "attendance": {"checked_in": 0, "confirmed": 0, "rate": 0.0},
  "payments": {"collected": "0.00", "pending": "0.00", "failed_count": 0},
  "budget": {"planned": "0.00", "actual": "0.00", "unpaid": "0.00",
             "net": "0.00"},
  "feedback": {"average_rating": null, "count": 0}
}
```

Definitions:

- `collected` is the sum of `completed` payments.
- `pending` is the sum of `amount_due` over `payment_pending`
  registrations.
- `unpaid` is the sum of `actual_amount`, falling back to `planned_amount`,
  over items where `paid=false`.
- `net` is `collected − actual`.
- `rate` is `checked_in / confirmed`, or 0 when there are no confirmed
  registrations.
- `by_day` is grouped by the registration's `registered_at` date.

### Frontend

- **Payments** placeholder → `PaymentsPage.jsx`: collected, pending and
  failed stat cards, plus a payments table with a status filter.
- **Analytics** placeholder → `AnalyticsPage.jsx`: stat cards, a Recharts
  line chart for `by_day` and a bar chart for `by_ticket_type`, the
  check-in rate, and the average rating.
- New **Budget** sidebar item → `BudgetPage.jsx`:
  - Summary strip: planned, actual, revenue, net (red when negative) and
    unpaid.
  - Line-item table with inline add, a paid toggle and delete.

Helpers go in `src/lib/finance.js`. `navigation.js` gains a Budget entry.

### Tests

- Summary numbers with a mix of registration and payment statuses and
  budget items, including zero-data events.
- Budget create, read, update and delete permissions.
- Payments list: organizer allowed; manager gets `403`.

---

## 4. USSD registration for free events

### Refactor

Move the body of `EventRegistrationView.post` into
`apps/events/services/registration.py`:

```python
class RegistrationError(Exception):
    def __init__(self, detail, http_status): ...

def register_for_event(event_id, user, ticket_type_id=None) -> EventRegistration
```

- Same locking, validation, capacity and re-registration behaviour.
- The `IntegrityError` and `OperationalError` handling is mapped to
  `RegistrationError` inside the function.
- A missing event raises `Http404`.
- The view calls the function and turns `RegistrationError` into
  `Response({"detail": ...}, status=...)`, so the API is unchanged.

### USSD

New main-menu option **4. Register for an event**. Options 1–3 keep their
numbers, and option 5 is Feature 2.

1. `CON Enter the event ID:`
2. Resolve the caller's user from `SMSPreference.phone_number == phoneNumber`.
   If there is no match, reply
   `END No Tuviora account uses this phone. Sign up at {FRONTEND_BASE_URL}/signup and add this number.`
3. Load the published event (`get_public_event`). If it is not found, reply
   `END Published event not found.`
4. Decide whether it is free:
   - No active ticket types: free, with `ticket_type_id=None`.
   - An active ticket type with `price == 0`: free, using the cheapest such
     ticket type.
   - Otherwise:
     `END This event requires payment. Register at {FRONTEND_BASE_URL}/events/{id}.`
5. `CON Register for {name}, {date:%d %b} {start_time:%H:%M}?\n1. Yes\n2. No`
6. On `1`, call `register_for_event`. On success, reply
   `END You're registered for {name}.` and, after the transaction commits,
   send a confirmation SMS if the user opted in. On `RegistrationError`,
   reply `END {detail}`. On `2`, reply `END Registration cancelled.`

### Tests

- Happy path: registration created and confirmed, and the SMS mocked and
  sent only with consent.
- Declining.
- Unknown phone.
- Paid event.
- Full event.
- Already registered.
- Invalid or unknown event ID.
- Every existing registration and concurrency test passes unchanged.

---

## Out of scope

- Inbound SMS replies; USSD covers feedback.
- Scheduled announcements at arbitrary times.
- Creating accounts over USSD.
- Paying over USSD.
- Separate vendor records.
- Multi-currency budgets.
