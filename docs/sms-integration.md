# Tuviora SMS Integration

Tuviora uses Africa's Talking for SMS notifications.

## Configuration

Set these variables in `backend/.env` (copy from the root `.env.example`):

    SMS_ENABLED=false
    AFRICASTALKING_USERNAME=sandbox
    AFRICASTALKING_API_KEY=your_sandbox_api_key
    AFRICASTALKING_SENDER_ID=

Never commit API credentials. SMS is disabled by default.

## Registration SMS

Users may provide an international phone number, such as
+256700123456, and explicitly opt in using sms_enabled.

Registration SMS is submitted after the database transaction
commits. SMS failure does not cancel account registration.

## Reusable SMS service

Import send_sms from apps.sms.services.sms_service.

The service validates phone numbers and messages, checks
configuration, and handles provider submission responses.

Provider acceptance does not guarantee final SMS delivery.

## Consent-aware event notifications

Import send_attendee_sms from
apps.sms.services.event_sms_notifications.

Supply explicit recipient user IDs and a message.

Only selected users with SMS consent and a saved phone
number are eligible.

The caller must verify event participation and organizer
approval before sending.

Import send_team_sms from the same module to message an
event's organizer and every accepted team member. Supply
the event and a message; it resolves recipients from
EventMembership internally, so callers do not pass user IDs.
Organizers and managers reach it through
`POST /api/events/<event_id>/team/message/`.

## Other SMS triggers

- Payment confirmation, sent when the MarzPay webhook confirms a
  registration.
- Organizer announcements (POST /api/events/<event_id>/announcements/) and the daily send_event_reminders command.
- USSD registration confirmation (option 4), sent only when the account has SMS consent.

(Readiness task assignments are notified by email, not SMS.)

## Sandbox testing

Use Africa's Talking sandbox credentials and authorized
test recipients. Enable SMS only during controlled testing.

Never expose API credentials in the frontend or Git.

## Automated tests

Run:

    .venv/bin/python backend/manage.py test

External SMS requests are mocked in automated tests.

## Pending integration

Event reminders, organizer-approved announcements and
targeted incident updates are not built yet. The attendee
registration API they depend on now exists.

Incident notifications must reach only affected attendees.
