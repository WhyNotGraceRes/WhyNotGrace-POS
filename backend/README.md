# WhyNotGrace — Backend

Modular restaurant + hotel operating system API. FastAPI + PostgreSQL +
SQLAlchemy 2.x + Alembic + JWT auth + Argon2id + Razorpay, built for
multi-tenant SaaS use with server-enforced feature flags and RBAC.

This is a real backend: PostgreSQL only (no SQLite, no in-memory mocks),
real Argon2id password hashing, real JWT + rotating refresh tokens, real
Razorpay signature verification, real audit logging.

## Requirements

- Python 3.12+
- PostgreSQL 16+ (via Docker Compose, or a local install)
- Docker + Docker Compose (optional, but recommended)

## Quick start (Docker)

```bash
cp .env.example .env
# edit .env if you want non-default credentials
docker compose up --build
```

This starts PostgreSQL, runs `alembic upgrade head`, then starts the API
at `http://localhost:8000`. It also builds and starts the frontend SPA
(nginx-served static build) at `http://localhost:3000` — see
`../frontend/Dockerfile` and `../frontend/.env.example`. The frontend
container is optional; nothing about the frontend requires Docker, and it
can equally be deployed to any static host (Vercel, Netlify, S3+CloudFront)
instead. To point the built frontend at a non-default backend URL, set
`FRONTEND_VITE_API_URL` before running `docker compose up --build` (it is
baked into the JS bundle at build time, since Vite reads `VITE_*` vars at
build time, not container runtime).

**Docker status:** the compose file and both Dockerfiles have been
validated with `docker compose config` (resolves build contexts, args,
healthchecks, and service dependencies correctly) but the actual image
builds have **not** been run end-to-end in this environment (no running
Docker daemon available here). Verify with a real `docker compose up --build`
before relying on it for a real deployment.

## Quick start (local Python, PostgreSQL via Docker only)

```bash
cp .env.example .env
docker compose up -d postgres
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Quick start (fully local PostgreSQL, no Docker)

1. Install PostgreSQL 16+ and create a database + user matching `.env`
   (`POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`).
2. `pip install -r requirements.txt`
3. `alembic upgrade head`
4. `uvicorn app.main:app --reload`

## Seeding development data

Creates two real, isolated businesses (Business A, Business B) with an
owner account, a menu item, and a table each — useful for manually
exercising tenant isolation:

```bash
python -m scripts.seed
```

Prints the seeded (development-only) owner credentials. Refuses to run
when `APP_ENV=production`.

## Running tests

Tests run against a **real PostgreSQL database** — point `TEST_DATABASE_URL`
at a disposable database (never your primary one; tables are created and
dropped):

```bash
createdb whynotgrace_test   # or: docker exec -it <postgres-container> createdb -U whynotgrace whynotgrace_test
TEST_DATABASE_URL=postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5432/whynotgrace_test pytest
```

Each test runs inside a rolled-back transaction, so the database returns
to its prior state after every test. The most important suite is
`tests/test_tenant_isolation.py` — it verifies Business A can never read,
modify, or enumerate Business B's data.

## Health checks

- `GET /health` — liveness only.
- `GET /health/db` — executes `SELECT 1` against PostgreSQL; returns 503
  if the database is unreachable. Never reports "ok" without a real query.

## API docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`

All routes are namespaced under `/api/v1` (see `app/core/config.py:api_v1_prefix`).

## Architecture

```
app/
  main.py            FastAPI app, router wiring, health checks, production-safety gate
  api/                One router module per resource group (auth, menu, orders, ...)
  core/
    config.py         Environment-driven settings + production safety validation
    security.py       Argon2id hashing, JWT issuance, secure token generation
    permissions.py    RBAC role groups
    dependencies.py   get_current_user / get_current_business_id / require_roles / require_feature
    encryption.py     At-rest encryption for integration credentials
  database/           Engine/session factory (PostgreSQL only) + declarative base
  models/             SQLAlchemy 2.x ORM models (45 tables) — see app/models/__init__.py
  schemas/            Pydantic v2 request/response models
  services/           Business logic, one module per domain
    payments/          PaymentProvider interface + Razorpay implementation
    integrations/      MarketplaceProvider interface + Zomato/Swiggy implementations
  utils/              Slugs, numbering, i18n lookup helpers
alembic/              Migrations (versions/0001_initial_schema.py creates all 45 tables)
tests/                pytest suite incl. tenant isolation, RBAC, auth, order/KOT/billing flow
scripts/seed.py       Development-only seed data
```

### Multi-tenancy

Every business-owned table carries `business_id`. It is **never** read
from a client-supplied path/query/body field for authenticated staff
endpoints — it is always derived from the JWT via
`get_current_business_id` (see `app/core/dependencies.py`). Public
endpoints (QR ordering, pickup/delivery checkout, the public website) are
scoped instead by an unguessable QR session token or business slug, never
a raw client-supplied business id.

### Feature flags

`FeatureFlag` rows are per-business. `require_feature(module)` /
`require_feature_for_business(...)` (see `app/core/dependencies.py`)
enforce them server-side on every gated endpoint — a frontend cannot
unlock a disabled module by calling the API directly. `CORE_POS` is
always on and cannot be disabled.

### Pricing

Prices are **only ever** resolved server-side (`app/services/pricing_service.py`).
Order/QR/pickup/delivery request schemas carry `menu_item_id` /
`variant_id` / `option_ids` — never a price. `PriceRule` rows give
context-specific pricing (dine-in vs. pickup vs. delivery vs. room
service vs. custom sections); the resolved price is frozen into
`OrderItem` at creation time.

### Order engine

One engine (`app/services/order_service.py`) backs dine-in, QR, room
service, pickup, delivery, and POS orders. `OrderSession` groups the
original + every additional order for one table/room visit so a single
bill covers all of them, and each additional order gets its own `Order`
+ `KOT` — so only newly added items are ever sent to the kitchen.

Pickup/delivery orders are created with `hold_kot=True`: the KOT is not
released to the kitchen until the Razorpay payment is verified
(`billing_service.record_payment_applied` calls
`kot_service.release_held_kots_for_session` once a bill reaches `PAID`).

### Payments

`app/services/payments/base.py` defines the `PaymentProvider` interface;
`razorpay_provider.py` is the only implementation today. A payment is
only ever marked `SUCCESS` after Razorpay's HMAC signature is verified
server-side (order creation → verify endpoint, or a signature-verified
webhook) — the frontend reporting success is never sufficient by itself.

Razorpay credentials can be configured **per business**
(`PUT /api/v1/integrations/RAZORPAY/credentials`, encrypted at rest the
same way as Zomato/Swiggy) or fall back to the global `RAZORPAY_KEY_ID` /
`RAZORPAY_KEY_SECRET` env vars for single-tenant deployments — see
`payment_service._resolve_razorpay_credentials`. Webhooks can be pointed
at either the legacy global-secret URL (`/payments/webhooks/razorpay`) or
a per-business URL (`/payments/webhooks/razorpay/{business_id}`) that
verifies against that business's own connected secret.

### Platform subscription (₹699/month)

`app/models/subscription.py` (`Subscription` + `SubscriptionPayment`) is a
deliberately separate concept from the Payments section above: a business
paying **the WhyNotGrace platform itself**, not a business's customer
paying the business. It is always verified against the platform's own
global `RAZORPAY_KEY_ID`/`SECRET` (never a business's connected Razorpay
credentials from the Integrations page — see
`app/services/subscription_service.py`'s module docstring). Real
one-shot payment + real HMAC signature verification, renewed manually
each month (not Razorpay's separate Subscriptions/autopay API, which
would need a pre-created Plan ID and UPI Autopay product access this
project doesn't have). `GET/POST /api/v1/subscription*`, OWNER-only.
Subscription status is informational only in this build — it is not
wired into any feature-flag or access-control gate.

### Integrations (Zomato / Swiggy)

`app/services/integrations/base.py` defines `MarketplaceProvider`.
`zomato_provider.py` / `swiggy_provider.py` implement it but require real
partner API credentials (`ZOMATO_API_BASE_URL` / `SWIGGY_API_BASE_URL`
+ connected credentials) — until those are supplied, every method raises
`IntegrationNotConfigured` (surfaced as HTTP 503) rather than fabricating
a response. Credentials are stored Fernet-encrypted
(`app/core/encryption.py`) and never echoed back via the API.

### Loyalty

`LoyaltyRule` rows are fully owner-configurable (`ORDER_COUNT_THRESHOLD`,
`SPEND_THRESHOLD`, `POINTS_PER_AMOUNT`, `CUSTOM`) — nothing is hardcoded.
Rules are evaluated in `app/services/loyalty_service.py` whenever a bill
reaches `PAID` for a known customer.

### Multi-language

`Translation` is a generic `(business_id, entity_type, entity_id,
field_name, language) -> value` table (`app/models/translation.py`), so
adding a language never requires new tables or duplicated backend logic.
`app/utils/i18n.py:translate()` looks up a translation and falls back to
the default-language value. Wired into the public QR menu endpoint today
(`?lang=hi`); the same helper can be used anywhere else content needs to
be localized.

### Security hardening

- **Refresh token rotation + reuse detection**: every `/auth/refresh` call
  revokes the presented token and issues a new one; presenting an
  already-revoked (i.e. previously rotated-out) token revokes the user's
  *entire* refresh-token chain, since reuse of a rotated-out token is the
  signature of a stolen token being used alongside the legitimate one.
- **Account lockout**: `LOGIN_MAX_ATTEMPTS` failed logins locks the
  account for `LOGIN_LOCKOUT_MINUTES` (see `auth_service.authenticate`).
- **Password-reset / verification-resend rate limiting**: both
  `/auth/forgot-password` and `/auth/resend-verification` enforce a
  cooldown between repeated requests for the same account, so neither can
  be used to email-bomb a victim's inbox. `forgot-password`'s cooldown is
  silent (same generic response either way) so it can't be used as an
  account-existence oracle; `resend-verification`'s does return a 429 with
  a wait time, which is acceptable there since that endpoint only reveals
  timing for accounts that are already known-unverified.
- **Response compression** — `GZipMiddleware` compresses any response over
  `GZIP_MINIMUM_SIZE_BYTES` (default 1000). Measured on the QR public menu:
  7,838 bytes → 2,422 bytes, a 69% reduction, which matters because that
  response is the highest-traffic one in the system and is served over
  restaurant WiFi and mobile data. `compresslevel` is deliberately 5 rather
  than gzip's default 9 — load-test profiling found the app CPU-bound with
  the database nearly idle, so spending extra CPU chasing the last few
  percent of ratio would work against the actual bottleneck.
- **Baseline HTTP security headers** (`X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
  and `Strict-Transport-Security` when `APP_ENV=production`) are set on
  every response — see `app/main.py:security_headers`.
- **Rate limiting** (`slowapi`, see `app/core/rate_limit.py`) is
  applied to the specific endpoints most worth protecting: `/auth/login`
  (10/min), `/auth/register` (5/hour), `/auth/verify-email` (10/min),
  `/auth/resend-verification` (5/min), `/auth/refresh` (30/min),
  `/auth/forgot-password` (5/min), `/auth/reset-password` (10/min),
  Razorpay order-create/verify (20/min), and the public QR-scan/QR-order/
  pickup-checkout/delivery-checkout endpoints (10–30/min). It is
  independent of and does not replace the account-level lockout/cooldowns
  above — both layers run. Razorpay webhook endpoints are deliberately
  **not** IP rate-limited (the caller is Razorpay's own infrastructure,
  already authenticated by HMAC signature; throttling risks dropping a
  legitimate burst of payment confirmations).

  **What each limit is keyed by, and why it is not always the IP.** Two
  distinct problems make a naive IP key wrong in production, and both are
  silent — the app works perfectly in development and misbehaves only once
  it is deployed:

  1. *Behind a reverse proxy, every request carries the proxy's IP.*
     `slowapi`'s own `get_remote_address` reads `request.client.host`, which
     in the `docker-compose.prod.yml` topology is always the `lb` nginx
     container. Every per-client limit therefore silently becomes ONE GLOBAL
     limit for the whole deployment — 20 QR orders per minute across every
     business on the platform. `app/core/client_ip.py` resolves the real
     client from `X-Forwarded-For`, but **only** from proxies declared in
     `TRUSTED_PROXY_IPS`, since that header is otherwise attacker-controlled
     and honoring it blindly would let anyone mint a fresh bucket per
     request. `validate_production_safety()` refuses to boot in production
     unless the setting is declared (use `none` to state deliberately that
     nothing sits in front).
  2. *A venue's guests all share one IP.* Every guest on a restaurant's WiFi
     is behind one NAT, and mobile users are behind carrier CGNAT. No proxy
     configuration fixes this. So the public QR endpoints are **not** keyed
     by IP: `POST /qr/orders` is keyed by the guest's QR session token
     (`qr_session_key`) and `GET /qr/scan/...` by the location being scanned
     (`qr_location_key`). The limit then reads "one table cannot place more
     than 20 orders a minute", which is both the thing actually worth
     enforcing and independent of how many guests share a public IP. A
     200-table venue gets 200 independent budgets rather than one.
     Pickup/delivery checkout stays IP-keyed — those customers order from
     their own connections — but is scoped per business
     (`public_checkout_key`) so one tenant cannot exhaust another's budget.

  **Known limitation, now configurable (Phase 11)**: the limiter's default
  storage is in-process memory, keyed per running process — with more than
  one worker (`--workers N` / multiple replicas), each worker enforces its
  own independent counter, so the *effective* limit across the whole
  deployment is `(configured limit) x (worker count)`, not the configured
  limit exactly. Setting `REDIS_URL` backs the limiter with Redis instead,
  giving an exact shared limit across every worker/instance — no call site
  needs to change either way. `app/core/rate_limit.py` checks Redis
  reachability *and* Lua-scripting support (`EVAL`) at startup and falls
  back to in-memory storage if either check fails, so a misconfigured or
  incompatible `REDIS_URL` degrades safely instead of breaking every
  rate-limited request. See "Scaling beyond one process" below.
- This does **not** replace a reverse-proxy/CDN-level limiter for
  general traffic shaping (e.g. protecting read-only GET endpoints from
  scraping, or absorbing a volumetric flood before it reaches the
  application at all) — see the reverse-proxy recommendation in the
  Deployment Guide below.

### Audit logging

`app/services/audit_service.py:record()` is called inside the same
transaction as the action it logs (login, registration, menu/price
changes, staff changes, order cancellation, KOT/bill/payment changes,
settings/feature-flag changes, integration changes, etc.), so the audit
entry and the change commit or roll back together.

### Scaling beyond one process (Phase 11)

**Connection-pool math.** Each `uvicorn` worker creates its own SQLAlchemy
pool of `DB_POOL_SIZE + DB_POOL_MAX_OVERFLOW` connections (default 10+20=30,
matching the original single-worker deployment exactly). Running N workers
or N horizontally-scaled instances means:

```
total_possible_connections = instances × workers_per_instance × (DB_POOL_SIZE + DB_POOL_MAX_OVERFLOW)
```

This must stay comfortably under PostgreSQL's `max_connections` (default
100), with headroom for `psql`, migrations, and any other client. **Do not
raise `DB_POOL_SIZE`/`DB_POOL_MAX_OVERFLOW` without first recomputing this
against your actual `max_connections` and actual worker/instance count** —
an unchecked increase is exactly how a multi-instance deployment silently
exhausts Postgres.

**Current recommended config: `DB_POOL_SIZE=5`, `DB_POOL_MAX_OVERFLOW=7`
(12 per worker × 4 workers = 48 total)** — the only configuration actually
verified clean, repeatably, at load (1,500 concurrent users, Phase 11, 3×).

A larger pool (8+12=20 per worker, 80 total, still comfortably under
`max_connections=100`) was tried in Phase 11.2 specifically to raise the
2,000-user ceiling, on reasonable evidence (at 2,000 users with the
48-connection pool, `pg_stat_activity` showed it repeatedly saturating at
48, each saturation event correlated with a permanent step-increase in
stuck `idle in transaction` connections). **That larger pool was tested
and rejected** — the mandatory regression check re-ran 1,000 concurrent
users (previously rock-solid clean, 4× verified) against it, and it
*failed*: 40 leaked connections, p99 latency jumped from ~2.5s to ~10s.
The most likely explanation: the actual constraint was never pool
*capacity* — a bigger pool just let more requests simultaneously hold a
connection while genuinely CPU/GIL-bound, so more of them piled up in the
slow state that triggers the leak, not fewer. **Do not deploy the 8+12
config based on this document** — it made things worse, not better; this
is recorded so the same wrong turn isn't taken twice. See the Phase 11.2
report for full evidence.

The underlying leak mechanism (see below) remains only partially
characterized after three dedicated investigations (Phase 10C, 11, 11.2)
— confirmed to be triggered by DB-pool saturation under sustained
concurrency, but never pinned to an exact line of code. **This is the
actual reason 2,000+ concurrent users is not currently safe**, not pool
sizing per se.

**Dashboard isolation from QR traffic (Phase "make it work").** The public
QR endpoints (`app/api/qr.py` — scan, menu, place order, order status) are
structurally isolated from the staff dashboard/kitchen/orders/admin routes,
at two separate layers, so a QR traffic surge cannot make the dashboard
unavailable:

1. **Separate DB connection pool.** `app/database/session.py` defines a
   second SQLAlchemy engine (`qr_engine`/`QRSessionLocal`, sized by
   `QR_DB_POOL_SIZE`/`QR_DB_POOL_MAX_OVERFLOW`, defaults 10+20) used *only*
   by `app/api/qr.py` via `get_qr_db()`. Every other route still uses the
   original `engine`/`SessionLocal` via `get_db()`. A QR surge that
   exhausts its pool cannot prevent staff routes from getting a connection
   — they draw from a different pool, not different slots of the same one.
2. **Separate request-thread budget.** This alone was tested and found
   **not sufficient**: a real Locust run (150 users hammering `/qr/menu`
   against a deliberately tiny 2-connection QR pool, concurrently with
   authenticated staff traffic polling `/api/v1/orders`) showed 0 errors on
   the staff side but a 52-second *median* staff latency — a dashboard
   that isn't technically down but is unusable. Root cause: FastAPI/
   Starlette dispatch every sync route and sync dependency (QR *and*
   staff alike) through one shared, process-wide `anyio` thread limiter
   (default capacity 40) regardless of which DB engine it queries. QR
   requests blocked waiting on the (saturated) QR pool were still holding
   threads the staff dashboard needed to run on at all.
   Fix: `app/api/qr.py`'s routes now dispatch their actual DB-query work
   through a QR-only `anyio.CapacityLimiter` (`app/core/request_limits.py`,
   sized by `QR_MAX_CONCURRENT_REQUESTS`, default 30) instead of the
   default limiter. `get_qr_db()` itself stays on the default limiter —
   it only constructs a `Session` object (no I/O), so it can't
   meaningfully compete with staff for those threads. Re-running the exact
   same overload test after this fix: staff `/orders` median latency
   dropped from 52,000ms to 3,800ms (a 13x improvement) with a ~3% error
   rate instead of a total freeze, 0 leaked DB connections, 0 server
   tracebacks.

**What this does and does not guarantee.** This makes the dashboard
*structurally* protected against QR-traffic overload on a single instance
— it cannot be starved of DB connections or completely starved of request
threads, even under a deliberately worst-case QR pool exhaustion test.
It does **not** eliminate all cross-traffic impact on one shared machine
(CPU, OS socket/accept-queue, and network contention still exist and were
visible as a residual few-percent staff error rate in that same test), and
it does **not** by itself raise the QR-traffic capacity ceiling — that
remains governed by the connection-pool math and the not-fully-root-caused
leak mechanism described above (~1,500 concurrent QR users, with caching,
is the highest number actually verified clean and repeatable). Genuine
10,000-concurrent-user capacity requires production infrastructure this
single-machine dev sandbox does not have: multiple server instances behind
a load balancer, managed Postgres/PgBouncer, and real Redis.

### Production deployment topology (`docker-compose.prod.yml`)

The infrastructure named as the actual path to real horizontal capacity —
multiple server instances behind a load balancer, PgBouncer, real Redis —
now exists as a deployable overlay:

```
internet -> lb (nginx, the only published port)
              |
              v
       backend replicas (N, --scale)  --workers 4 each
              |
              v
          pgbouncer  (transaction pooling)
              |
              v
          postgres
                                    redis (cache + rate limiting)
```

```bash
# One-time: real credentials, never committed
cp deploy/pgbouncer/userlist.txt.example deploy/pgbouncer/userlist.txt
# edit it — see the file's own instructions (query pg_shadow for the exact
# md5 hash, don't hand-type one)

cp .env.production.example .env   # then fill in every CHANGE-ME

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    up -d --scale backend=${BACKEND_REPLICAS:-3}
```

**What each piece is for, and why it's structured this way:**

- **`lb` (nginx, `deploy/nginx/nginx.conf`)** — the only container with a
  published host port. Load-balances across every running `backend`
  replica using open-source nginx's `resolve` upstream parameter
  (available since nginx 1.27.3 without a commercial license — this was
  checked against nginx's own documentation before relying on it, not
  assumed) combined with Docker's embedded DNS (`127.0.0.11`), so
  `docker compose up -d --scale backend=N` is picked up without restarting
  nginx. Failover is nginx's own passive `max_fails`/`fail_timeout`
  tracking on real proxy-level failures — **not** Docker DNS excluding
  unhealthy containers, which was checked and confirmed to **not** happen
  in plain (non-swarm) Compose: Docker's embedded DNS returns every
  replica's IP regardless of `HEALTHCHECK` status, unlike Swarm's routing
  mesh. A replica failing its own healthcheck is also failing real
  requests, so nginx routes around it within `max_fails` tries regardless
  of what Docker's DNS reports — the mechanism is real, just not the one
  it would be easy to assume.
- **`backend` (scaled via `--scale`, not `deploy.replicas`)** — `--scale`
  is used in the documented command specifically because it's honored by
  plain `docker compose up` on every Compose version; `deploy.replicas`
  is a Swarm-mode key that only some newer Compose versions also apply to
  non-swarm `up`, which would make the documented command version-
  dependent for no benefit. No host port of its own — reachable only
  through `lb`, on the internal compose network.
- **`migrate`** — runs `alembic upgrade head` exactly **once**, before any
  `backend` replica starts (`depends_on: condition: service_completed_successfully`).
  The base `docker-compose.yml` ran migrations from the backend's own
  startup command, which is fine for one instance but unsafe once there's
  more than one replica — N containers racing to run schema DDL
  concurrently against the same database is a real anti-pattern, not a
  hypothetical one. Connects directly to `postgres`, not through
  `pgbouncer`: DDL wants normal session semantics, not transaction
  pooling.
- **`pgbouncer` (`deploy/pgbouncer/pgbouncer.ini`, transaction pooling)** —
  every backend replica/worker's `DATABASE_URL` points here, never
  directly at `postgres`. This is what decouples "how many replicas and
  workers we run" from Postgres's `max_connections` ceiling: a real
  Postgres backend connection is only held for the duration of one
  transaction, then returned to PgBouncer's pool (`default_pool_size=25`)
  for the next waiting client, instead of one connection being pinned to
  one app-side pool slot for its entire lifetime. Updated connection
  math:

  ```
  app-side connections (against pgbouncer) = replicas × UVICORN_WORKERS × (staff pool + QR pool)
  real Postgres connections used           = pgbouncer's default_pool_size (25, regardless of the above)
  ```

  Example: 3 replicas × 4 workers × (12 staff + 25 QR) = 444 connections
  against pgbouncer (`max_client_conn=2000` headroom), while Postgres
  itself only ever sees ~25 real connections from the app — comfortably
  under `max_connections=100` with room for `psql`/other clients, no
  matter how many replicas are added. **Important caveat, handled, not
  ignored**: PgBouncer's transaction-pooling mode is incompatible with
  server-side prepared statements (a statement prepared on one real
  connection can vanish when the next transaction lands on a different
  one). Both SQLAlchemy engines in `app/database/session.py` now set
  `connect_args={"prepare_threshold": None}`, unconditionally, to disable
  psycopg3's server-side prepared-statement cache — verified safe (full
  pytest suite still 108/108 passing) whether or not PgBouncer is
  actually in front. **What PgBouncer does not do**: it doesn't fix the
  residual, not-fully-root-caused `idle in transaction` leak mechanism
  from earlier phases — that's a connection-*lifecycle* bug, not a
  connection-*count* ceiling, and the two are independent problems that
  happen to both be about database connections.
- **Resource limits** (`mem_limit`/`cpus` on every service) — the older,
  universally-supported Compose keys (not the Swarm-only `deploy.resources`
  block), so a runaway replica can't starve the whole host, on any Compose
  version, without needing swarm mode.
- **TLS** — deliberately not hand-rolled here. `lb`'s nginx.conf listens
  on plain HTTP; the README recommends terminating TLS at a managed cloud
  load balancer (ALB/GCP LB/Cloudflare) placed in front of it in a real
  deployment, for automated certificate rotation and DDoS absorption
  neither this repo nor a hand-rolled certbot container would give you as
  reliably. If you must terminate on this box directly, `nginx.conf` has
  a comment marking exactly where a `listen 443 ssl;` block belongs.

**Honest verification status.** This machine has the `docker` and
`docker compose` CLIs installed but no usable Docker daemon (no Docker
Desktop running, none installed) — confirmed by direct check, the same
constraint every earlier load-testing phase in this project ran into.
This means:
- **Verified, locally, for real**: `docker compose config` against the
  merged base+prod files parses and interpolates correctly, every host
  port is confirmed absent from `postgres`/`redis`/`backend` and present
  only on `lb`/`frontend`, `migrate` is confirmed `restart: "no"` with the
  correct `service_completed_successfully` gate, and every volume mount
  path resolves as intended. The specific nginx `resolve` + Docker-DNS-
  does-not-exclude-unhealthy-containers claims above were checked against
  nginx's and the wider Docker ecosystem's own documentation rather than
  assumed — one initial assumption (Docker DNS excluding unhealthy
  containers) was checked and found **wrong** before it was written down
  as fact anywhere, and the design was changed to rely on nginx's real
  passive health tracking instead.
- **Not verified here, by necessity**: actually running
  `docker compose -f docker-compose.yml -f docker-compose.prod.yml up`,
  because no Docker daemon exists in this sandbox to run it against. The
  PgBouncer image (`edoburu/pgbouncer`) and its config format are
  correctly authored per that image's own documentation, not smoke-tested
  live. **Before trusting this in production, run it once on a real
  Docker host and confirm**: all services report healthy
  (`docker compose ps`), `docker compose exec backend curl -f
  http://localhost:8000/health/db` succeeds (proves the pgbouncer hop
  works end-to-end), a QR menu load and a staff login both succeed through
  `lb`'s published port, and `docker compose up -d --scale backend=2` then
  killing one replica leaves the app fully working (proves the LB
  failover). This is a smoke test any real deployment should do once
  regardless of who wrote the compose files.

**Public menu caching.** `app/core/cache.py` is an optional read-through
cache for the QR public-menu response (`qr_service.build_menu_response`) —
the highest-traffic, read-heavy endpoint in the whole system. Disabled by
default (`REDIS_URL` unset); every cache call becomes a no-op and the app
falls straight through to PostgreSQL, identical to pre-Phase-11 behavior.
When enabled:
- Keys are tenant-scoped by construction: `business:{business_id}:public_menu:{location_type}:{language}` — there is no code path that can look up or delete another business's key.
- TTL defaults to 60s (`PUBLIC_MENU_CACHE_TTL_SECONDS`) and is the actual staleness guarantee.
- A SQLAlchemy `after_commit` hook (`app/database/session.py`) invalidates a business's cached menu automatically whenever any commit touches its `menu_categories`/`menu_items`/`menu_variants`/`menu_option_groups`/`menu_options`/`price_rules` rows — no per-endpoint invalidation call was hand-added to the 15+ menu/category/pricing mutation routes.
- If Redis is unreachable at any point (including after having worked), every read/write/invalidate call catches the error, logs a warning, and falls back to querying Postgres directly — a Redis outage degrades performance, not correctness or availability.
- **Never cache**: order state, payment verification, authorization decisions, or anything tenant-sensitive beyond the public menu — this module is intentionally only ever called from the one public, unauthenticated, non-transactional read path.

**Distributed rate limiting.** The same `REDIS_URL`, if set, also backs
`app/core/rate_limit.py`'s storage (see "Security hardening" above) — an
exact shared limit across every worker/instance instead of a per-process
approximation. Startup checks both Redis reachability *and* Lua-scripting
(`EVAL`) support before committing to it, falling back to in-memory
storage on either failure — discovered to matter in practice: not every
Redis-protocol-compatible server implements Lua scripting (`limits`'s
atomic increment-and-check depends on it).

**What was actually verified** (see the Phase 11 load-test report for full
numbers): with caching enabled, 1,500 concurrent public QR users ran
clean and repeatably (3 consecutive runs, 0 real 5xx, 0 leaked database
connections each time) — the same concurrency level that failed on
connection-leak grounds without caching, because caching removes the vast
majority of menu-read traffic from the database connection pool entirely,
which was the actual precondition for the leak to trigger. **This is not
verified for 2,000+ concurrent users** — see `backend/loadtest/README.md`
for the exact staged results and what remains untested.

## Environment variables

See `.env.example` for the full list with comments. Production startup
(`app.core.config.Settings.validate_production_safety`, called from
`app/main.py`'s lifespan) refuses to boot if `APP_ENV=production` and any
of the following hold:

- `JWT_SECRET` is the development placeholder or under 32 characters
- `DEBUG=true`
- `EMAIL_BACKEND=console`
- `POSTGRES_PASSWORD` looks like a development placeholder
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` are missing

## Feature status matrix

**IMPLEMENTED** (works today, no further setup):
- Auth (register/verify/login/refresh/logout/reset), RBAC, tenant
  isolation, feature flags, menu + contextual pricing, orders/KOT/kitchen,
  tables/rooms/QR ordering, billing + cash payments, loyalty rules +
  redemption, reviews, reports, audit logging, multi-language (en/hi/mr),
  the ₹699/month platform subscription's data model, RBAC, tenant
  isolation, and signature-verification logic (the Razorpay order-create
  API call itself needs real credentials — see EXTERNAL CREDENTIALS below)

**CONFIGURATION REQUIRED** (real capability, needs env vars / an admin
action, no external account signup):
- **SMTP email** — set `EMAIL_BACKEND=smtp` + `SMTP_*`; `EMAIL_BACKEND=console`
  (development only) logs emails to stdout instead of sending them, and
  is refused at startup when `APP_ENV=production`.
- **Docker deployment** — `docker compose up --build` (see above); needs a
  running Docker daemon, which this development environment does not have.

**EXTERNAL CREDENTIALS REQUIRED** (architecture-complete, but needs a
real third-party account before it does anything):
- **Razorpay** — functional as soon as either a business connects its own
  credentials (`PUT /api/v1/integrations/RAZORPAY/credentials`) or the
  global `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET`
  env vars are set; until then, order-creation and webhook endpoints
  return HTTP 503 rather than faking success. Needs a real Razorpay
  account (test or live mode) to actually process a payment. The
  ₹699/month platform subscription (`POST /api/v1/subscription/checkout`)
  always uses the global env vars specifically — a business's own
  connected credentials never apply to its own subscription payment.
- **Zomato integration** — needs a Zomato Partner API agreement
  (`ZOMATO_API_BASE_URL`, client id/secret connected via
  `PUT /api/v1/integrations/ZOMATO/credentials`); until connected, every
  call returns HTTP 503 rather than fabricating a response.
- **Swiggy integration** — same, via `SWIGGY_API_BASE_URL` +
  `PUT /api/v1/integrations/SWIGGY/credentials`.

**NOT IMPLEMENTED**:
- Rate limiting on every endpoint (only the sensitive ones listed under
  Security hardening — general GET/list endpoints are not throttled at
  the application level; put a reverse-proxy/CDN limiter in front for
  that, see the Deployment Guide).
- A shared (cross-worker/cross-instance) rate-limit counter — the
  in-memory default is per-process (see Security hardening above);
  requires Redis to fix for a multi-worker deployment.
- Platform-wide superadmin operations across businesses (this is a
  per-tenant SaaS backend; `app/api/admin.py` is owner-scoped audit-log
  access only, not a cross-tenant admin panel).

## Deployment Guide

### A. Local development

```bash
cp .env.example .env
python -m venv .venv && source .venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
docker compose up -d postgres   # or a local PostgreSQL install — see B
alembic upgrade head
uvicorn app.main:app --reload
```
Frontend: see `../frontend/README.md`.

### B. PostgreSQL setup

Either `docker compose up -d postgres` (uses the `postgres` service in
`docker-compose.yml`, persisted to the `postgres_data` named volume — see
N), or install PostgreSQL 16+ locally and create a database + user
matching your `.env`'s `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`.
`app/database/session.py` refuses to start against anything but a
`postgresql://` URL — there is no SQLite fallback, in development or
production.

### C. Docker setup

`Dockerfile` (backend) is a single-stage `python:3.12-slim` build that
installs `requirements.txt`, copies the app, and runs as a non-root `app`
user. `../frontend/Dockerfile` is a multi-stage build (Node build stage →
nginx-alpine runtime stage, also non-root, listening on 8080 internally).
Both have `HEALTHCHECK` instructions and a `.dockerignore` (critical for
the frontend image in particular — without it, `COPY . .` would ship the
host's `node_modules` into the Linux image, silently breaking on any
platform-specific native binary).

**Docker verification status in this environment: the Docker daemon is
not available here** (`docker version` succeeds for the client but
cannot reach the daemon). What *has* been verified without a daemon:
`docker compose config` resolves both services' build contexts, build
args, healthchecks, and dependency ordering correctly. What has **not**
been verified: that `docker build` actually succeeds for either image,
or that the running containers behave correctly together. Run a real
`docker compose up --build` and work through section P (Troubleshooting)
before trusting this for a real deployment.

### D. Docker Compose startup

```bash
cp .env.example .env   # edit for your setup — see F
docker compose up --build
```
Starts, in dependency order: `postgres` (waits for its healthcheck) →
`backend` (runs `alembic upgrade head` then `uvicorn`) → `frontend`
(nginx serving the build). Backend on `http://localhost:8000`, frontend
on `http://localhost:3000`. To rebuild the frontend against a different
API URL: `FRONTEND_VITE_API_URL=https://api.example.com docker compose up --build`
(see G — this is a build arg, baked in at build time, not read at
container runtime).

### E. Database migrations

`alembic upgrade head` — run automatically by the `backend` service's
compose command before `uvicorn` starts; run manually for any other
deployment target (bare-metal, ECS task, etc.) as a one-off step before
starting the app. Migrations live in `alembic/versions/`, applied in
their `down_revision` chain order (currently `0001_initial_schema` →
`0002_menu_crud_and_delivery`). Never edit an already-applied migration
file; add a new one. `alembic downgrade -1` reverts the most recent one
if needed (verify against a backup first in production — see M).

### F. Environment variables

See `.env.example` (development reference — safe defaults, all
placeholder secrets) and `.env.production.example` (documents every
variable that must be a *real* value in production, and why). Categories:
database, JWT/auth, CORS, frontend URL, Razorpay, SMTP, Zomato, Swiggy,
application environment (`APP_ENV`/`DEBUG`), QR sessions. There is no
separate "logging" env var group — logging level follows `DEBUG` (`INFO`
when false, `DEBUG` when true; see `app/main.py`).
`Settings.validate_production_safety()` (`app/core/config.py`) refuses to
boot when `APP_ENV=production` and any of: `JWT_SECRET` is the dev
placeholder or under 32 chars, `DEBUG=true`, `EMAIL_BACKEND=console`,
`POSTGRES_PASSWORD` looks like a placeholder, Razorpay global credentials
are missing, or `CORS_ORIGINS` contains `*`.

### G. Production frontend configuration

`VITE_API_URL` is the only frontend env var, and it's a public URL (not
a secret) — see `../frontend/.env.production.example`. It must be
supplied as a **Docker build arg** (`FRONTEND_VITE_API_URL` in
`docker-compose.yml`, or `--build-arg VITE_API_URL=...` for a manual
`docker build`), never as a container runtime environment variable —
Vite bakes `VITE_*` values into the JS bundle at build time. The
frontend bundles zero backend secrets of any kind.

### H. Production backend configuration

Copy `.env.production.example`'s guidance into a real `.env` (or your
platform's secret manager — see below), fill in every `CHANGE-ME`, set
`APP_ENV=production`, and let `validate_production_safety()` be the
final check at boot. Prefer injecting secrets via your platform's native
mechanism (AWS Secrets Manager / Parameter Store, GCP Secret Manager,
Kubernetes Secrets, Fly.io secrets, etc.) over a plain `.env` file on
disk where one is available — `docker-compose.yml`'s `env_file: .env` is
the simple/local/single-host path, not a requirement.

### I. HTTPS / reverse proxy recommendation

Neither container terminates TLS itself. Put a reverse proxy in front in
production — e.g. nginx, Caddy, Traefik, or your cloud provider's load
balancer (ALB, Cloud Load Balancing) — that:
- terminates HTTPS (Let's Encrypt via Caddy/Traefik is the simplest path)
- forwards `backend:8000` and `frontend:8080` behind their public paths
- sets `X-Forwarded-For` / `X-Forwarded-Proto` correctly (slowapi's
  `get_remote_address` key function reads `request.client.host`, which
  is only accurate behind a proxy if it forwards the real client IP —
  e.g. nginx's `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
  plus trusting that header; consult `limits`/`slowapi` docs if you need
  the limiter to key off the forwarded IP instead of the proxy's own)
- optionally adds volumetric/general-purpose rate limiting
  (nginx `limit_req_zone`/`limit_req`, or your CDN's built-in limiter) —
  this is the general-purpose layer the application-level limiter
  intentionally doesn't try to be (see Security hardening above)
- optionally adds a `Content-Security-Policy` header — not set by the
  app itself, since a CSP tight enough to be meaningful has to be
  hand-tuned per deployment (font/analytics/CDN origins vary), and a
  wrong one silently breaks the app rather than failing loudly

### J. Razorpay production setup

1. Create a live-mode Razorpay account, get `Key ID` / `Key Secret` from
   their dashboard.
2. Either set them as `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` (global
   fallback, used by any business that hasn't connected its own), or
   have each business connect its own via
   `PUT /api/v1/integrations/RAZORPAY/credentials` (OWNER role only).
3. Configure a webhook in the Razorpay dashboard pointing at
   `https://your-api-domain/api/v1/payments/webhooks/razorpay` (global
   secret) or `.../payments/webhooks/razorpay/{business_id}` (that
   business's own connected `webhook_secret`) — set `RAZORPAY_WEBHOOK_SECRET`
   (global) or include `webhook_secret` in that business's connected
   credentials to match.
4. This has not been tested against real Razorpay traffic in this
   environment (no live/test credentials available here) — the security
   architecture (signature verification, per-business credential
   isolation, encrypted-at-rest storage) has been verified with real
   HMAC computations in `tests/test_integration_security.py`, not a real
   Razorpay account.

### K. SMTP setup

Set `EMAIL_BACKEND=smtp` + `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/
`SMTP_PASSWORD`/`SMTP_FROM`/`SMTP_USE_TLS`. Any standard SMTP provider
works (SES, Postmark, SendGrid, etc.) — `app/services/email_service.py`
uses plain `smtplib`, no provider-specific SDK. `EMAIL_BACKEND=console`
(logs instead of sending) is refused at startup when `APP_ENV=production`.

### L. Zomato / Swiggy credentials

Both need a real Partner API agreement with Zomato/Swiggy respectively —
there is no self-serve API key generation for either. Set
`ZOMATO_API_BASE_URL`/`SWIGGY_API_BASE_URL` once you have partner API
access, then connect each business's client id/secret via
`PUT /api/v1/integrations/{ZOMATO,SWIGGY}/credentials`. Until both the
env var and the per-business credentials are set, every call to that
provider correctly returns HTTP 503 rather than fabricating a response.

### M. Backup recommendation

`postgres_data` is the only stateful data in this stack (the backend and
frontend containers are both fully stateless/replaceable). At minimum:
automated daily `pg_dump` (or your managed provider's automated
snapshots, e.g. RDS automated backups) retained for a meaningful window,
stored off the same host/volume, with a periodic *restore* drill — an
untested backup is not a backup. If you self-host Postgres via the
`postgres` compose service, back up the `postgres_data` volume directly
in addition to (not instead of) logical `pg_dump`s, since a volume
snapshot restores faster but a logical dump survives a Postgres major
version upgrade.

### N. Database persistence

`docker-compose.yml` declares `postgres_data` as a named volume mounted
at `/var/lib/postgresql/data`, so data survives `docker compose down` /
container recreation (it does **not** survive `docker compose down -v`,
which explicitly removes volumes — never run that against a deployment
with real data). For a managed database (RDS/Cloud SQL/etc.) instead of
the `postgres` compose service, persistence is the provider's
responsibility and the `postgres_data` volume simply goes unused.

### O. Health checks

- `GET /health` — liveness only, no dependencies checked.
- `GET /health/db` — executes a real `SELECT 1` against PostgreSQL;
  returns 503 (not "ok") if the database is unreachable.
- Both Dockerfiles declare a `HEALTHCHECK` (backend: `curl /health`;
  frontend: `wget` against nginx's root) so `docker ps` / orchestrator
  health probes reflect real container state.
- `postgres`'s compose healthcheck (`pg_isready`) is what `backend`'s
  `depends_on: condition: service_healthy` waits on before starting.

### P. Troubleshooting

- **Backend won't start, "Refusing to start in production due to
  insecure configuration"**: read the listed errors — each maps directly
  to a `.env` value described in F/H above. This is
  `validate_production_safety()` working as intended, not a bug.
- **Backend can't reach PostgreSQL**: confirm `DATABASE_URL` (or the
  `POSTGRES_*` pieces it's built from) point at a reachable host from
  *inside* the backend container — `localhost` inside the backend
  container is the container itself, not the `postgres` service; use the
  service name (`postgres`) as configured in `docker-compose.yml`'s
  `DATABASE_URL` override.
- **Frontend loads but every API call fails / CORS error in the
  browser console**: `VITE_API_URL` was baked in wrong at build time
  (rebuild — it can't be fixed by changing a running container's env),
  or the backend's `CORS_ORIGINS` doesn't include the frontend's actual
  origin.
- **Frontend deep link (e.g. `/menu`) 404s on a hard refresh**: this is
  exactly what `nginx.conf`'s `try_files $uri $uri/ /index.html;`
  fallback exists to prevent — if it's still happening, confirm the
  built `nginx.conf` inside the image matches the one in the repo (stale
  image layer).
- **`alembic upgrade head` fails on startup**: check it's pointed at an
  empty/already-migrated database, not one with conflicting manually-made
  schema changes — this project's migrations are the only sanctioned way
  to change schema (see the project rule against manual DB edits).
- **Rate-limit (429) responses appearing for legitimate traffic**: if
  running multiple backend workers/replicas, remember the effective
  limit is `(configured) x (worker count)` — see the Security hardening
  section's rate-limiting note; consider Redis-backed storage or looser
  per-worker limits.
