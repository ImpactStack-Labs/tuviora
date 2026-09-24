# Tuviora Architecture

Frontend: React, Vite and Tailwind CSS.

Backend: Django and Django REST Framework.

AI: OpenAI API, accessed exclusively through Django.

Telecommunications: Africa's Talking SMS, USSD
and Voice, accessed through Django.

Payments: MarzPay (wallet.wearemarz.com) Mobile Money and
card collections, accessed through Django. See
[Payments](../payments/README.md).

Database: SQLite for initial local development,
with PostgreSQL planned for deployment.

All sensitive credentials belong in environment variables.
