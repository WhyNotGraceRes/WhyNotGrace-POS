# WhyNotGrace load testing

Load/scalability test tooling for the public QR ordering flow. See the
Phase 10 Load & Scalability Report for full results — this file just
documents how to reproduce the setup.

## Isolated environment

Never run this against the dev or production database. It targets its own
Postgres **database** (`whynotgrace_loadtest`, on the same portable Postgres
**server** already used for local dev/tests — see repo root context) and its
own backend **process**, on a separate port from the dev server:

```bash
# 1. Create + migrate the isolated database (once)
psql -h localhost -p 5544 -U whynotgrace -d postgres -c "CREATE DATABASE whynotgrace_loadtest OWNER whynotgrace;"
DATABASE_URL=postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5544/whynotgrace_loadtest alembic upgrade head

# 2. Seed test data (one hotel with a realistic menu + 50 tables, one small
#    "isolation control" business, and pre-provisioned QR sessions)
DATABASE_URL=postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5544/whynotgrace_loadtest \
    python -m loadtest.seed_loadtest --sessions 5000 --isolation-sessions 100 --tables 50

# 3. Start a DEDICATED backend instance for the load test (separate port,
#    separate DB, separate process from any dev server)
DATABASE_URL=postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5544/whynotgrace_loadtest \
    uvicorn app.main:app --host 0.0.0.0 --port 8100
```

## Running a staged test

```bash
pip install -r loadtest/requirements.txt

# server-side metrics, run alongside Locust
python loadtest/collect_metrics.py --port 8100 --out loadtest/results/stageN_metrics.csv --duration 200 &

# the load itself — MixedHotelUser is the primary "realistic hotel rush" scenario
locust -f loadtest/locustfile.py --host http://localhost:8100 \
    -u <users> -r <spawn-rate> --run-time <seconds> --headless \
    --csv loadtest/results/stageN MixedHotelUser IsolationControlUser
```

## Why sessions are pre-provisioned, not scanned live

`GET /qr/scan/...` is rate-limited to 30/min **per source IP**
(`app/core/rate_limit.py`). A Locust load generator runs from a single
machine/IP, so every simulated user's traffic collapses into that one
bucket — a real limitation of testing from one machine, not of the app
(5,000 real guests would have 5,000 real IPs). `seed_loadtest.py` inserts
`QRSession` rows directly (same model/table the real endpoint writes to),
so the *actual load test* still exercises menu-loading, order-placement,
and status-polling over real HTTP against the real app — only the one-time
"scan" step is pre-provisioned, matching how a real guest only scans once
before the sustained traffic begins.

`POST /qr/orders` (20/min per IP) is NOT bypassed — the load test hits it
for real and the locustfile treats HTTP 429 from it as an expected,
non-failing response, logging the true reason in the final report rather
than silently working around it.

## Testing with caching enabled (Phase 11)

No real Redis server is available in this environment (Docker is also
unavailable — see the main README). `run_fake_redis_server.py` starts
`fakeredis`'s real TCP server — a genuine, separate, network-reachable
process speaking the actual Redis wire protocol, backed by an in-memory
emulator (explicitly **not** genuine Redis; its Lua-scripting support is
incomplete — see app/core/rate_limit.py's startup capability check, added
specifically because of this). This is enough to test the real
application code path (redis-py client, connection handling, tenant-scoped
keys, cross-process cache sharing across all 4 uvicorn workers) — it does
**not** prove genuine Redis's own performance/operational behavior.

```bash
# Start the fake Redis TCP server (separate process, stays running)
python loadtest/run_fake_redis_server.py 6399

# Start the load-test backend with caching enabled
DATABASE_URL=postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5544/whynotgrace_loadtest \
    DB_POOL_SIZE=5 DB_POOL_MAX_OVERFLOW=7 REDIS_URL=redis://127.0.0.1:6399/0 \
    uvicorn app.main:app --host 0.0.0.0 --port 8100 --workers 4
```

Then run stages exactly as above. See the Phase 11 report for the
before/after comparison this produced at 1,000 and 1,500 concurrent users.
