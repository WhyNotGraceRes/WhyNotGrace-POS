# WhyNotGrace

A multi-tenant restaurant & hotel operating system — POS, QR ordering, kitchen
display, billing, loyalty, and reporting — built as SaaS: any number of
businesses sign up, each fully isolated from the others.

| | Stack |
|---|---|
| **[`backend/`](backend/)** | FastAPI · PostgreSQL 16 · SQLAlchemy 2.x · Alembic · JWT + Argon2id · Razorpay |
| **[`frontend/`](frontend/)** | Vite · React 19 · TypeScript · Tailwind 4 · TanStack Query · Zustand |

~9k lines of backend Python across 114 endpoints and 47 tables, ~18k lines of
frontend TypeScript, and 108 pytest tests that run against a real PostgreSQL
database (no SQLite, no mocks).

## What it does

- **POS** — dine-in, pickup, and delivery orders from one screen, with
  server-priced variants and option groups.
- **QR ordering** — a guest scans the QR on their table and orders from their
  own phone. No app, no login.
- **Kitchen display** — live KOT tickets. When a table adds a second round,
  the kitchen only ever sees the *new* items.
- **Billing** — one bill per table visit no matter how many orders it took,
  with tax, service charge, discounts, and cash or Razorpay settlement.
- **Loyalty, customers, reviews, reports, audit log, staff & RBAC.**
- **Three languages** — English, Hindi, Marathi.

## Getting started

Each half has its own setup guide — start with the backend:

- **[backend/README.md](backend/README.md)** — local setup, Docker, migrations,
  deployment guide, and an honest feature-status matrix
- **[frontend/README.md](frontend/README.md)** — dev server, build, API type
  generation

Short version:

```bash
cd backend && cp .env.example .env && python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m scripts.seed && .venv/bin/uvicorn app.main:app --reload
```

```bash
cd frontend && cp .env.example .env && npm install && npm run dev
```

Backend requires **Python 3.12** (the pinned dependencies have no wheels for
3.13+). The seed script prints development-only owner credentials for two
isolated demo businesses.

## Design principles

These four decisions shape most of the codebase:

1. **`business_id` is never client-supplied.** On authenticated endpoints it is
   always derived from the JWT — never from a path, query, or body field.
   Public endpoints (QR, pickup, delivery) are scoped by an unguessable session
   token or business slug instead. `tests/test_tenant_isolation.py` proves
   Business A cannot read, modify, or enumerate Business B.
2. **Prices are resolved server-side, always.** Clients send item, variant, and
   option ids — never a price. `PriceRule` rows make the same dish cost
   differently for dine-in vs. pickup vs. delivery vs. room service, and the
   resolved price is frozen into the order so later menu edits can't rewrite
   history.
3. **One order engine for every channel.** Dine-in, QR, room service, pickup,
   delivery, and POS all go through `order_service.create_order()`.
   `OrderSession` groups a table's whole visit into one bill while giving each
   round its own kitchen ticket.
4. **Feature flags are enforced by the server.** Hiding a nav item in React is
   a UX nicety; `require_feature()` is the actual gate, so a disabled module
   can't be unlocked by calling the API directly.

## Security

Argon2id password hashing · rotating refresh tokens with reuse detection ·
account lockout · Razorpay HMAC verified server-side · integration credentials
Fernet-encrypted at rest · audit entries written in the same transaction as the
action they record · a production-safety gate that refuses to boot with
development secrets.

See the Security hardening section of [backend/README.md](backend/README.md)
for the full list, including what is deliberately *not* covered.

## Load testing

[`backend/loadtest/`](backend/loadtest/) holds the Locust setup and the raw
CSV results from staged runs at 250 → 2,000 concurrent users. Verified clean
and repeatable at **1,500 concurrent QR users**; higher is explicitly not
claimed. The backend README documents both what was fixed (a connection leak
traced to Starlette's `BaseHTTPMiddleware`, and dashboard starvation traced to
FastAPI's shared thread limiter) and what was tried and rejected.
