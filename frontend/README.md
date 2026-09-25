# Tuviora Frontend

React 19 + Vite single-page app for Tuviora's public site, attendee
experience and organizer operations workspace. Styling is Tailwind CSS 4;
maps use Leaflet; ticket QR codes use `qrcode.react` (display) and
`html5-qrcode` (scanning).

## Run locally

Start the Django backend first (see the [main README](../README.md)), then:

```bash
npm install
npm run dev
```

The dev server runs at `http://localhost:5173/` and proxies every `/api`
request to Django at `http://127.0.0.1:8000` (see `vite.config.js`), so
the browser only ever talks to one origin.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server with hot reload |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | ESLint |
| `node src/lib/format.check.mjs` | Regression check for date/time formatting |

## Authentication

The app uses Django session cookies. `src/lib/auth.js` first calls
`/api/auth/csrf/` to set the `csrftoken` cookie, then sends it as
`X-CSRFToken` on every write request with `credentials: 'same-origin'`.
Never put API keys or provider credentials in frontend code — all
integrations (OpenAI, Africa's Talking, MarzPay) are called by the backend.

## Routes

Defined in `src/App.jsx`:

| Path | Page |
| --- | --- |
| `/` | Public home |
| `/events`, `/events/:eventId` | Published event list and detail (register, pay) |
| `/my-registrations` | Attendee's registrations and tickets |
| `/attendee/login`, `/signup`, `/verify-email` | Attendee authentication |
| `/invite` | Accept a team invitation |
| `/operations/*` | Organizer and team workspace |

`/operations` (`OperationsPage`) decides what to show from `/api/auth/me/`:
signed-out users get `OrganizerLogin`; non-organizers who hold
accepted team memberships get `TeamWorkspace` (their assigned tasks and
incidents); organizers get the full workspace
(`src/layouts/OrganizerLayout.jsx`, sidebar items in
`src/components/organizer/navigation.js`):

| Section | Page |
| --- | --- |
| Overview | `OrganizerOverview` |
| My Events, create event | `MyEvents`, `CreateEvent` |
| Event Readiness | `EventReadiness` (tasks) |
| Event Team | `EventTeam` (invitations, team SMS) |
| Registration | `EventRegistrations` |
| Attendance | `EventAttendance` (QR check-in) |
| Live Operations | `LiveOperations` |
| Incident Management | `IncidentManagement` (incl. critical-incident team calls) |
| Payments | `PaymentsPage` |
| Budget | `BudgetPage` |
| Communications | `Communications` (SMS announcements) |
| Feedback | `FeedbackPage` (incl. AI summary) |
| Analytics | `AnalyticsPage` |

## Source layout

```text
src/
├── App.jsx            # top-level routes
├── pages/             # one component per screen
├── layouts/           # OrganizerLayout (operations workspace shell)
├── components/        # shared UI, maps/, organizer/ sidebar
└── lib/               # API helpers: auth, events, team, readiness,
                       # conference, formatting
```
