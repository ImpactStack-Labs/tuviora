# USSD sandbox testing

The Django callback is `POST /api/ussd/callback/`. It receives Africa's Talking
`sessionId`, `serviceCode`, `phoneNumber`, and cumulative `text` form fields.
Responses begin with `CON` to continue a session or `END` to finish it.

## Run locally

From the repository root, activate the Python virtual environment, then run:

    python backend/manage.py migrate
    python backend/manage.py runserver 127.0.0.1:8000

For an external sandbox test, expose port 8000 through a temporary HTTPS tunnel.
Allow only that tunnel's hostname in Django's `ALLOWED_HOSTS` for the test, and
keep `DEBUG` off while the tunnel is public. In Africa's Talking sandbox, create
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
- Registration status and staff incident reporting currently end without revealing
  private data or accepting a report. They require verified phone ownership;
  staff reporting additionally requires accepted event membership and a staff PIN
  or equivalent authentication.

The simulator test uses a local development database. Creating a channel does
not deploy the Django backend. Do not commit tunnel hostnames, credentials, or
private phone numbers.
