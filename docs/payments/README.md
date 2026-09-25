# Tuviora Payments (MarzPay)

Tuviora collects paid-event registration payments through
**MarzPay** (https://wallet.wearemarz.com), which supports Mobile Money
push payments and card checkout. This satisfies the payments
requirements in the [project brief](../product-brief/README.md#7-payments):
Tuviora never holds attendee funds — MarzPay processes the transaction
and Tuviora only records the resulting reference, amount, method,
status and date against the attendee's registration.

## Status

**Implemented; not yet live-tested against MarzPay.** The `Payment`
model, the initiate endpoint, the signed webhook, `apps/events/services/marzpay_service.py`
and ticket types with prices are all in place and covered by automated
tests (`test_payments_api.py`, `test_marzpay_service.py`) with MarzPay
mocked. The original build plans are in
[`docs/superpowers/plans/`](../superpowers/plans/).

Before going live, run a sandbox collection end to end and confirm the
webhook reaches a publicly reachable `MARZPAY_CALLBACK_URL`.

## How it works

1. An attendee with a `payment_pending` registration chooses Mobile
   Money or Card and calls
   `POST /api/events/<event_id>/registrations/me/pay/` with `method`
   (`mobile_money` or `card`) and, for Mobile Money, `phone_number`.
2. Tuviora creates a `pending` `Payment` row and calls MarzPay's
   `/collect-money` endpoint. This sends a Mobile Money prompt to the
   attendee's phone, or returns a card checkout URL. A second request
   while a payment is in progress is rejected.
3. MarzPay processes the payment asynchronously and calls Tuviora's
   webhook, `POST /api/payments/marzpay/webhook/`.
4. The webhook verifies the `X-MarzPay-Signature` HMAC-SHA256 header
   (with `X-MarzPay-Timestamp`) and updates the `Payment` status. Only on
   `collection.completed` does it move the `EventRegistration` from
   `payment_pending` to `confirmed` and send the confirmation SMS.
   Webhooks for unknown references are acknowledged and ignored.

A registration is confirmed only by the webhook, never by the initiate
call, because Mobile Money collections do not complete synchronously.

## Configuration

Set these variables in `backend/.env` (copy from the root `.env.example`):

    MARZPAY_BASE_URL=https://wallet.wearemarz.com/api/v1
    MARZPAY_API_KEY=
    MARZPAY_API_SECRET=
    MARZPAY_WEBHOOK_SECRET=
    MARZPAY_CALLBACK_URL=
    MARZPAY_DEFAULT_COUNTRY=UG

Never commit real MarzPay API keys, secrets or webhook secrets.

## Payment statuses

`pending` → `processing` → `completed` | `failed` | `cancelled`,
matching MarzPay's own transaction states. Refunds are outside the
MVP (brief §15) and are not modeled.

## Scope limits

Single-market MVP: the `country` field sent to MarzPay is a fixed
setting (`MARZPAY_DEFAULT_COUNTRY`), not resolved per attendee.
Expanding beyond Uganda requires resolving `country` from the
attendee's phone prefix or an organizer-set field.
