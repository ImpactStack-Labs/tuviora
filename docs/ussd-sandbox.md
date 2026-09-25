# USSD sandbox testing

The Django callback is `POST /api/ussd/callback/`. It receives Africa's Talking
`sessionId`, `serviceCode`, `phoneNumber`, and cumulative `text` form fields.
Responses begin with `CON` to continue a session or `END` to finish it.

## Run locally

From the repository root, activate the Python virtual environment, then run:

    python backend/manage.py migrate
    python backend/manage.py runserver 127.0.0.1:8000

For an external sandbox test, expose port 8000 through a temporary HTTPS tunnel.
Set `DJANGO_ALLOWED_HOSTS` in `backend/.env` to only that tunnel's hostname for
the test, and keep `DEBUG` off (`DJANGO_DEBUG=False`, which requires
`DJANGO_SECRET_KEY`) while the tunnel is public. In Africa's Talking sandbox, create
a USSD channel on the shared `*384#` code. Set its Callback URL to:

    https://YOUR-TUNNEL-HOST/api/ussd/callback/

Launch the web simulator and dial the full code assigned to the channel.
A temporary tunnel address changes when restarted; update the Callback URL and
allowed hostname when that happens. Stop the tunnel after testing.

## Flows to check

- The opening menu lists event information, registration, staff reporting, and exit.
- Choose `1`, then enter the ID of a published event in the local database.
  The response shows its public name, date, time, and venue.
- An unknown event ID ends with "Published event not found."
- Enter `8`, then `0` to check that exit works after an invalid choice.
- Choose `2`, then enter the ID of an event. The response shows the registration
  status, ticket type, and amount due for whichever Tuviora account has that
  event registration and the caller's own phone number (Africa's Talking's
  `phoneNumber` field, not user-typed input) saved as its SMS preference. No
  match, in either the account or the specific event registration, ends with
  the same generic "No registration found for this event." to avoid revealing
  which phone numbers have a Tuviora account.
- Staff incident reporting currently ends without accepting a report. It
  requires accepted event membership and a staff PIN or equivalent
  authentication.

The simulator test uses a local development database. Creating a channel does
not deploy the Django backend. Do not commit tunnel hostnames, credentials, or
private phone numbers.
