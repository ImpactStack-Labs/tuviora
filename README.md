# Tuviora

**Inclusive, AI-assisted event management for better planning, coordination and participation.**

Tuviora is an event management platform designed to bring event organizers, team members and attendees into one connected experience. It combines event discovery, registration, team coordination, readiness tracking and communication, with integrations for accessible mobile services.

The project is under active development.

## The problem

Organizing an event often requires managing information across disconnected tools. Registration, team assignments, event preparation, attendee communication and on-site operations can become difficult to coordinate.

Tuviora brings these workflows together in one platform while exploring accessible channels for people who may not have reliable internet access or smartphones.

## Core features

### Event discovery and registration

Attendees can browse published upcoming events, view event details, sign up (with email verification), register for events, cancel a registration and view all their registrations in My Registrations.

Events can offer ticket types with prices. Free registrations are confirmed immediately; paid registrations stay `payment_pending` until payment completes. Confirmed attendees receive a ticket with a QR code.

### Payments

Paid registrations are collected through MarzPay by Mobile Money or card. Registrations are confirmed only by MarzPay's signed webhook, which also triggers a confirmation SMS. See [Payments](docs/payments/README.md).

### Event organization

Organizers create, manage and publish events from the operations workspace (`/operations`), which includes an overview, My Events, event creation, registrations and ticket-type management.

### Team collaboration

Organizers invite team members by email and assign the **manager** or **member** role. Invitees accept through an invitation link and gain access to the team workspace. Organizers and managers can send an SMS to the whole event team.

### Event readiness

Organizers create readiness tasks and assign them to team members. Members see only their assigned tasks and can update task status; the organizer controls titles, deadlines and assignees. Assignees are notified of new tasks by email.

### Attendance and check-in

The organizer and team members check attendees in by scanning the ticket QR code or entering the ticket reference. Only confirmed tickets can be checked in, and each ticket only once.

### Live operations and incidents

Team members report incidents by category and severity during an event. The organizer and managers update incident status. For **critical** incidents they can trigger automated voice calls to the organizer and event managers (behind `VOICE_CRITICAL_CALLS_ENABLED`).

### AI assistance

Using OpenAI through the backend API (no frontend screens yet), organizers can:

- request an AI analysis of an incident (classification, suggested severity, priority, recommended actions and a draft message), which they must approve before it is acted on;
- collect attendee feedback and generate an AI summary of it.

### Maps and venue information

Venue search and map components (Leaflet) support location-based event information.

### Accessible channels (Africa's Talking)

- **SMS:** registration welcome, payment confirmation and team messages; always opt-in and disabled by default. See [SMS integration](docs/sms-integration.md).
- **USSD:** look up a published event and check your own registration status from a basic phone. See [USSD sandbox](docs/ussd-sandbox.md).
- **Voice:** a multilingual voice menu (English, Kiswahili, Luganda) using Sunbird AI text-to-speech.

The private voice conference backend is still in development: organizer-controlled conference management, membership-based access and one-time access codes exist, but live conference calling is not ready. See [Voice Services](backend/apps/voice_services/README.md).

### Planned capabilities

Expanded USSD features (such as staff incident reporting), organizer-approved attendee announcements, conference frontend controls and deployment. Integrations should not be treated as production-ready until live end-to-end testing is complete.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite 8 |
| Styling | Tailwind CSS 4 |
| Navigation | React Router |
| Icons | Lucide React |
| Charts | Recharts |
| Maps | Leaflet, React Leaflet |
| QR codes | qrcode.react, html5-qrcode |
| Backend | Python, Django |
| API | Django REST Framework |
| Development database | SQLite |
| Communication integrations | Africa's Talking (SMS, USSD, voice) |
| Payments | MarzPay (Mobile Money, card) |
| AI | OpenAI API, Sunbird AI text-to-speech |
| Email | Brevo SMTP (console backend in development) |
| Conference session infrastructure | Redis, when configured |
| Version control | Git and GitHub |

## Project structure

```text
tuviora/
├── backend/
│   ├── apps/
│   │   ├── accounts/        # sign-up, email verification
│   │   ├── events/          # events, registrations, tickets, payments,
│   │   │                    # team, tasks, incidents, feedback, AI
│   │   ├── sms/             # SMS service and consent preferences
│   │   ├── ussd/            # USSD callback
│   │   └── voice_services/  # voice menu, conferences, incident calls
│   ├── config/              # settings, root URLs, auth endpoints
│   ├── .env                 # your local settings (not committed)
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── lib/
│   │   └── pages/
│   └── package.json
├── docs/
│   └── superpowers/         # implementation plans and design specs
├── .env.example
└── README.md
```

## Getting started

### Prerequisites

Install the following:

- Python and pip
- Node.js and npm
- Git

Redis is additionally required for shared conference session state when the conference feature is enabled.

### 1. Clone the repository

```bash
git clone https://github.com/ImpactStack-Labs/tuviora.git
cd tuviora
```

Use the integration branch for current team development:

```bash
git fetch origin
git switch dev
git pull origin dev
```

Create your own feature branch before making changes.

### 2. Configure environment variables

Copy the example environment file into `backend/`, which is where Django loads it from:

```bash
cp .env.example backend/.env
```

Update `backend/.env` with your own development settings and any credentials required for the integrations you are working on.

Never commit `backend/.env`, API keys, access tokens or other secrets.

Some integrations require additional provider configuration. Refer to the relevant module documentation before enabling them.

### 3. Set up the backend

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Apply database migrations:

```bash
python backend/manage.py migrate
```

Start the development server:

```bash
python backend/manage.py runserver
```

By default, Django runs at `http://127.0.0.1:8000/`.

### 4. Set up the frontend

Open another terminal in the project directory:

```bash
cd frontend
npm install
npm run dev
```

Vite displays the local frontend URL, typically
`http://localhost:5173/`.

Keep the backend running in its own terminal while developing features that use the API.

## Environment configuration

`.env.example` lists every setting the backend reads. Copy it to `backend/.env`.

| Group | Variables | Needed for |
| --- | --- | --- |
| Django | `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` | `DEBUG` is off unless `DJANGO_DEBUG=True`; with it off, Django refuses to start without `DJANGO_SECRET_KEY`. Allowed hosts default to `localhost,127.0.0.1`. |
| Email | `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `EMAIL_HOST`, `EMAIL_PORT` | Sending verification emails. If unset, emails are printed to the Django console. |
| AI | `OPENAI_API_KEY`, `OPENAI_MODEL`, `SUNBIRD_API_KEY` | Incident and feedback analysis, and voice text-to-speech |
| Africa's Talking | `SMS_ENABLED`, `AFRICASTALKING_USERNAME`, `AFRICASTALKING_API_KEY`, `AFRICASTALKING_SENDER_ID` | SMS; voice calls also use the username and API key |
| Voice | `AT_VOICE_NUMBER`, `AT_VOICE_CALLBACK_URL`, `REDIS_URL`, `VOICE_CONFERENCE_ENABLED`, `VOICE_CONFERENCE_MAX_PARTICIPANTS`, `VOICE_CRITICAL_CALLS_ENABLED` | Conferences and critical-incident calls |
| Payments | `MARZPAY_*` | MarzPay collections and webhook verification |

For local development, keep `DJANGO_DEBUG=True` from the example file. In any shared or public environment, set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY` and the real hostnames in `DJANGO_ALLOWED_HOSTS`.

Voice conferencing must remain disabled until callback authentication, shared session infrastructure and live integration testing are complete.

## Running tests

Run the backend application tests from the backend directory:

```bash
cd backend
python manage.py test apps
```

Check the Django configuration:

```bash
python manage.py check
```

Build the frontend, run the linter and run the date-formatting check from the frontend directory:

```bash
cd ../frontend
npm run build
npm run lint
node src/lib/format.check.mjs
```

A successful build or automated test run does not, by itself, confirm that external integrations are ready for production.

## Development workflow

Tuviora uses feature branches and pull requests.

1. Update your local `dev` branch.
2. Create a branch for your assigned issue.
3. Implement and test your changes.
4. Commit with a descriptive message.
5. Push your feature branch.
6. Open a pull request targeting `dev`.
7. Request review and complete any required changes before merging.

Do not push unfinished feature work directly to `main`.

## Documentation

[Documentation index](docs/README.md)

Detailed documentation is maintained in the `docs/` directory and alongside relevant application modules.

Key references:

- [API reference](docs/api/README.md)
- [Frontend guide](frontend/README.md)
- [Voice Services](backend/apps/voice_services/README.md)

## Current development priorities

- Move to PostgreSQL for deployment.
- Live-test MarzPay collections and webhooks end to end.
- Complete USSD staff incident reporting (requires staff authentication).
- Add organizer-approved attendee announcements and targeted incident updates over SMS.
- Authenticate incoming voice callbacks and finish private conference calling.
- Build the conference frontend controls.
- Complete deployment and end-to-end application testing.

## Repository

[ImpactStack Labs — Tuviora](https://github.com/ImpactStack-Labs/tuviora)

## Project status

**Active development.** Some application features are implemented and tested locally; others remain in development. Production availability and external-provider integration should be verified separately.
