# Tuviora Architecture

```text
React SPA (Vite)  ──/api proxy──▶  Django + DRF  ──▶  SQLite (dev) / PostgreSQL (planned)
                                      │
                                      ├─▶ OpenAI          (incident & feedback analysis)
                                      ├─▶ Sunbird AI      (voice text-to-speech)
                                      ├─▶ Africa's Talking (SMS, USSD, voice)
                                      ├─▶ MarzPay         (Mobile Money & card, via webhook)
                                      ├─▶ Brevo SMTP      (verification email)
                                      └─▶ Redis           (conference sessions & rate limits, optional)
```

**Frontend:** React 19, Vite and Tailwind CSS. It talks only to the
Django API, using session cookies and CSRF. See the
[frontend README](../../frontend/README.md).

**Backend:** Django and Django REST Framework, split into apps:

| App | Responsibility |
| --- | --- |
| `accounts` | Sign-up, email verification |
| `events` | Events, ticket types, registrations, tickets and check-in, payments, team and invitations, readiness tasks, incidents, feedback, AI analysis (`events/services/`) |
| `sms` | SMS sending service, consent (`SMSPreference`), attendee and team notifications |
| `ussd` | Africa's Talking USSD callback |
| `voice_services` | Multilingual voice menu, private conferences, critical-incident calls |

Session auth endpoints live in `config/auth_views.py`.

**External services:** every provider is called only from Django, so
credentials never reach the browser. Provider callbacks (MarzPay webhook,
USSD, voice) enter through dedicated endpoints. See the
[API reference](../api/README.md).

**Database:** SQLite (`backend/db.sqlite3`) for local development;
PostgreSQL is planned for deployment.

**Configuration:** all credentials belong in `backend/.env`, loaded by
`backend/config/settings.py`. `DEBUG` is off by default, and
`DJANGO_SECRET_KEY` is required whenever it is off.
