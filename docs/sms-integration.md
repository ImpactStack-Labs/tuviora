# Tuviora SMS Integration

Tuviora uses Africa's Talking for SMS notifications.

## Configuration

Set these variables in backend/.env:

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

Import send_sms from apps.events.services.sms_service.

The service validates phone numbers and messages, checks
configuration, and handles provider submission responses.

Provider acceptance does not guarantee final SMS delivery.

## Consent-aware event notifications

Import send_event_sms from
apps.events.services.event_sms_notifications.

Supply explicit recipient user IDs and a message.

Only selected users with SMS consent and a saved phone
number are eligible.

The caller must verify event participation and organizer
approval before sending.

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
targeted incident updates require the attendee registration
API contract.

Incident notifications must reach only affected attendees.
