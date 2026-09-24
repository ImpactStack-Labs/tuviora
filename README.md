# Tuviora

**Inclusive, AI-assisted event management for better planning, coordination and participation.**

Tuviora is an event management platform designed to bring event organizers, team members and attendees into one connected experience. It combines event discovery, registration, team coordination, readiness tracking and communication, with integrations for accessible mobile services.

The project is under active development.

## The problem

Organizing an event often requires managing information across disconnected tools. Registration, team assignments, event preparation, attendee communication and on-site operations can become difficult to coordinate.

Tuviora brings these workflows together in one platform while exploring accessible channels for people who may not have reliable internet access or smartphones.

## Core features

### Event discovery and registration

Attendees can discover published events, view event details, create accounts, register for events and manage their registrations.

The application includes attendee login, signup and a dedicated My Registrations experience.

### Event organization

Organizers can create and manage events through a dedicated workspace.

The frontend includes event creation, event management, organizer overview and event registration screens.

### Team collaboration

Organizers can invite team members and assign event roles. Accepted members can access the relevant team workspace.

Event permissions distinguish organizers, managers, team members and users without accepted membership.

### Event readiness

The application includes an event readiness interface to support preparation and coordination before an event.

### Maps and venue information

Venue search and map components support location-based event information.

### Communication and accessible services

Tuviora includes work on Africa's Talking integrations for SMS, USSD and voice services.

The existing multilingual voice menu provides event information and navigation in supported languages.

The private voice conference backend is under development. It includes organizer-controlled conference management, membership-based access and one-time access codes, but live conference calling is not yet ready.

### Planned and developing capabilities

The broader product roadmap includes payment integration, expanded USSD registration, attendance and check-in workflows, further communication automation and AI-assisted functionality.

These capabilities should not be treated as production-ready until their integrations and end-to-end testing are complete.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite 8 |
| Styling | Tailwind CSS 4 |
| Navigation | React Router |
| Icons | Lucide React |
| Charts | Recharts |
| Maps | Leaflet, React Leaflet |
| Backend | Python, Django |
| API | Django REST Framework |
| Development database | SQLite |
| Communication integrations | Africa's Talking |
| Conference session infrastructure | Redis, when configured |
| Version control | Git and GitHub |

## Project structure

```text
tuviora/
├── backend/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── events/
│   │   ├── ussd/
│   │   └── voice_services/
│   ├── config/
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

Copy the example environment file:

```bash
cp .env.example .env
```

Update `.env` with your own development settings and any credentials required for the integrations you are working on.

Never commit `.env`, API keys, access tokens or other secrets.

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

The root `.env.example` documents the available application settings.

These include Django configuration, Africa's Talking credentials, optional AI integration settings and the developing voice conference configuration.

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

Build the frontend from the frontend directory:

```bash
cd frontend
npm run build
```

Run the frontend linter:

```bash
npm run lint
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

For the voice services and developing private conference integration, see
[Voice Services](backend/apps/voice_services/README.md).

## Current development priorities

- Complete and verify accessible USSD registration workflows.
- Complete SMS integration and end-to-end communication testing.
- Develop attendance and check-in functionality.
- Complete payment integration.
- Authenticate incoming voice callbacks and finish private conference calling.
- Build and test the remaining conference frontend controls.
- Complete deployment and end-to-end application testing.

## Repository

[ImpactStack Labs — Tuviora](https://github.com/ImpactStack-Labs/tuviora)

## Project status

**Active development.** Some application features are implemented and tested locally; others remain in development. Production availability and external-provider integration should be verified separately.
