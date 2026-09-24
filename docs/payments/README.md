# Tuviora Payments (MarzPay)

Tuviora collects paid-event registration payments through
**MarzPay** (https://wallet.wearemarz.com), which supports Mobile Money
push payments and card checkout. This satisfies the payments
requirements in the [project brief](../product-brief/README.md#7-payments):
Tuviora never holds attendee funds — MarzPay processes the transaction
and Tuviora only records the resulting reference, amount, method,
status and date against the attendee's registration.

## Status

**Not yet implemented.** The full task-by-task build plan lives at
[`docs/superpowers/plans/2026-09-24-marzpay-payments.md`](../superpowers/plans/2026-09-24-marzpay-payments.md)
and depends on ticket types/pricing
([`docs/superpowers/plans/2026-09-24-ticket-types-pricing.md`](../superpowers/plans/2026-09-24-ticket-types-pricing.md))
landing first. This document describes the intended integration; treat
any endpoint or model below as planned until that plan is executed.

## How it will work

1. An attendee with a `payment_pending` registration chooses Mobile
   Money or Card and calls
   `POST /api/events/<event_id>/registrations/me/pay/`.
2. Tuviora creates a `Payment` row (`pending`) and calls MarzPay's
   `/collect-money` endpoint — a Mobile Money push to the attendee's
   phone, or a card redirect URL.
3. MarzPay processes the payment asynchronously and calls Tuviora's
   webhook, `POST /api/payments/marzpay/webhook/`, once the collection
   reaches a final state (`completed`, `failed` or `cancelled`).
4. The webhook verifies MarzPay's `X-MarzPay-Signature` HMAC-SHA256
   header, updates the `Payment` status, and — only on
   `collection.completed` — flips the `EventRegistration` from
   `payment_pending` to `confirmed` and sends the confirmation SMS.

Registration is only ever confirmed from the webhook, never from the
initiate call, since Mobile Money collections do not complete
synchronously.

## Configuration

Set these variables in `backend/.env` (see `.env.example`):

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
