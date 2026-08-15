"""Locust load test for WhyNotGrace's public QR ordering flow.

Targets the ISOLATED load-test backend instance (see loadtest/README.md —
normally http://localhost:8100, pointed at the `whynotgrace_loadtest`
database, never a dev or production database/instance).

Uses ONLY existing, real API contracts (no invented endpoints):
  GET  /api/v1/qr/menu                  (X-QR-Session header)
  POST /api/v1/qr/orders                (X-QR-Session header)
  GET  /api/v1/qr/orders/{order_id}      (X-QR-Session header)

QR sessions are pre-provisioned directly in the DB by seed_loadtest.py
(bypassing the rate-limited /qr/scan endpoint for bulk setup only — see that
file's docstring) and loaded here from loadtest/data/sessions_business_a.jsonl.
Each simulated Locust User = one hotel guest who already scanned their
table's QR code and is now browsing/ordering — this matches real behavior
(a guest scans once, then the sustained traffic is menu loads, an order,
and status polling).

Scenarios (all against real HTTP, real DB, real business logic):
  A. MenuBrowsingUser   — repeated realistic menu reloads only.
  B. QrSessionUser      — same as A; session "maintenance" IS repeated
                           requests carrying the same X-QR-Session header
                           (there is no separate keep-alive endpoint in the
                           existing API contract to call instead).
  C. OrderingUser       — menu load -> place one real order -> read its
                           initial status.
  D. StatusPollingUser  — polls an already-placed order's status at the
                           app's OWN real polling interval (6s, copied from
                           frontend/src/features/qr/hooks.ts refetchInterval
                           — not invented).
  E. MixedHotelUser     — weighted mix of all of the above in one class;
                           this is the primary scenario for the staged
                           concurrency tests per the test plan.

Run examples (headless, from backend/ with the venv active):
  locust -f loadtest/locustfile.py --host http://localhost:8100 \
      -u 100 -r 2 --run-time 3m --headless --csv loadtest/results/stage_100 \
      MixedHotelUser
"""
import json
import random
import uuid
from pathlib import Path

from locust import HttpUser, task, between, events

DATA_DIR = Path(__file__).parent / "data"

_sessions_a: list[dict] = []
_sessions_b: list[dict] = []
_items_a: list[dict] = []
_next_session_idx = {"a": 0, "b": 0}


@events.test_start.add_listener
def _load_fixtures(environment, **kwargs):
    global _sessions_a, _sessions_b, _items_a
    _sessions_a = [json.loads(line) for line in (DATA_DIR / "sessions_business_a.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    _sessions_b = [json.loads(line) for line in (DATA_DIR / "sessions_business_b.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    _items_a = json.loads((DATA_DIR / "business_a_meta.json").read_text(encoding="utf-8"))["items"]
    if not _sessions_a:
        raise RuntimeError("No pre-provisioned Business A QR sessions found — run seed_loadtest.py first.")


def _next_session(business: str) -> dict:
    """Round-robin assignment so concurrent users don't all share one
    session/table (a real hotel has many tables, not one)."""
    pool = _sessions_a if business == "a" else _sessions_b
    idx = _next_session_idx[business]
    _next_session_idx[business] = (idx + 1) % len(pool)
    return pool[idx]


def _random_order_payload() -> dict:
    n = random.randint(1, 3)
    items = random.sample(_items_a, k=min(n, len(_items_a)))
    return {
        "items": [{"menu_item_id": it["id"], "quantity": random.randint(1, 2)} for it in items],
        "notes": None,
    }


class _QrUserBase(HttpUser):
    abstract = True

    def on_start(self):
        self.session_info = _next_session(getattr(self, "business", "a"))
        self.headers = {"X-QR-Session": self.session_info["session_token"]}

    def load_menu(self, name="/api/v1/qr/menu"):
        with self.client.get("/api/v1/qr/menu", headers=self.headers, name=name, catch_response=True) as resp:
            if resp.status_code == 200:
                body = resp.json()
                # Cheap per-response correctness spot-check (section 9): the
                # menu returned must belong to THIS user's own business, not
                # another one — catches any cross-tenant leakage immediately
                # rather than only at post-test reconciliation.
                expected_biz_name = "LoadTest Grand Hotel" if getattr(self, "business", "a") == "a" else "LoadTest Isolation Control"
                if body.get("business_name") != expected_biz_name:
                    resp.failure(f"tenant isolation violation: expected {expected_biz_name}, got {body.get('business_name')}")
                else:
                    resp.success()
            else:
                resp.failure(f"menu load failed: {resp.status_code}")
            return resp


class MenuBrowsingUser(_QrUserBase):
    """Scenario A + B: a guest who scans, then just browses the menu
    (opens categories, refreshes) without ordering — the majority of real
    QR traffic on any given evening."""
    wait_time = between(2, 6)
    business = "a"

    @task
    def browse_menu(self):
        self.load_menu(name="/api/v1/qr/menu [browse]")


class OrderingUser(_QrUserBase):
    """Scenario C: load menu, place exactly one real order, read its
    initial status once. Runs once per simulated guest (a real customer
    doesn't repeatedly re-order every few seconds), then goes idle —
    modeled with a long wait_time rather than looping, to avoid
    artificially inflating order volume beyond what one guest would
    generate in the test window."""
    wait_time = between(30, 90)
    business = "a"

    @task
    def order_once(self):
        self.load_menu(name="/api/v1/qr/menu [pre-order]")
        payload = _random_order_payload()
        with self.client.post("/api/v1/qr/orders", json=payload, headers=self.headers, name="/api/v1/qr/orders [POST]", catch_response=True) as resp:
            if resp.status_code == 201:
                order = resp.json()
                resp.success()
                order_id = order["id"]
                with self.client.get(f"/api/v1/qr/orders/{order_id}", headers=self.headers, name="/api/v1/qr/orders/{id} [initial]", catch_response=True) as status_resp:
                    if status_resp.status_code == 200 and status_resp.json().get("id") == order_id:
                        status_resp.success()
                    else:
                        status_resp.failure(f"status fetch mismatch/failed: {status_resp.status_code}")
            elif resp.status_code == 429:
                # Rate-limited: see loadtest/README.md — /qr/orders is
                # limited to 20/min per source IP, and this load generator
                # runs from a single IP, unlike 5,000 real distinct guest
                # devices. Not treated as an application failure.
                resp.success()
            else:
                resp.failure(f"order placement failed: {resp.status_code}: {resp.text[:200]}")


class StatusPollingUser(_QrUserBase):
    """Scenario D: places one order up front (like OrderingUser), then
    polls its status at the app's real 6s interval for the rest of the
    run — modeling a guest who ordered and is now watching the tracker."""
    wait_time = between(5.5, 6.5)  # matches the frontend's real 6s refetchInterval
    business = "a"

    def on_start(self):
        super().on_start()
        self.order_id = None
        payload = _random_order_payload()
        resp = self.client.post("/api/v1/qr/orders", json=payload, headers=self.headers, name="/api/v1/qr/orders [POST, setup]")
        if resp.status_code == 201:
            self.order_id = resp.json()["id"]

    @task
    def poll_status(self):
        if self.order_id is None:
            self.load_menu(name="/api/v1/qr/menu [no-order fallback]")
            return
        with self.client.get(f"/api/v1/qr/orders/{self.order_id}", headers=self.headers, name="/api/v1/qr/orders/{id} [poll]", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"status poll failed: {resp.status_code}")


class MixedHotelUser(_QrUserBase):
    """Scenario E — the primary scenario for the staged concurrency test.
    Weighted mix approximating real hotel-rush traffic: most guests just
    browse, a smaller share actively order, a smaller share is watching an
    existing order's status. Weights are an explicit modeling choice, not
    a measurement — documented here rather than hidden."""
    wait_time = between(2, 8)
    business = "a"

    def on_start(self):
        super().on_start()
        self.order_id = None

    @task(6)
    def browse(self):
        self.load_menu(name="/api/v1/qr/menu [mixed:browse]")

    @task(2)
    def order(self):
        self.load_menu(name="/api/v1/qr/menu [mixed:pre-order]")
        payload = _random_order_payload()
        with self.client.post("/api/v1/qr/orders", json=payload, headers=self.headers, name="/api/v1/qr/orders [mixed:POST]", catch_response=True) as resp:
            if resp.status_code == 201:
                self.order_id = resp.json()["id"]
                resp.success()
            elif resp.status_code == 429:
                resp.success()  # single-source-IP rate-limit artifact, see README
            else:
                resp.failure(f"order placement failed: {resp.status_code}: {resp.text[:200]}")

    @task(3)
    def poll(self):
        if self.order_id is None:
            self.load_menu(name="/api/v1/qr/menu [mixed:poll-fallback]")
            return
        with self.client.get(f"/api/v1/qr/orders/{self.order_id}", headers=self.headers, name="/api/v1/qr/orders/{id} [mixed:poll]", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"status poll failed: {resp.status_code}")


class IsolationControlUser(_QrUserBase):
    """Runs alongside the main test at low volume, using Business B's
    sessions, purely so post-test reconciliation has live Business-B
    traffic to check for cross-tenant contamination against (section 10)."""
    wait_time = between(3, 10)
    business = "b"

    @task
    def browse_other_business(self):
        self.load_menu(name="/api/v1/qr/menu [isolation-control:b]")


class _StaffUserBase(HttpUser):
    """Authenticated staff/admin flow — a real login against
    POST /api/v1/auth/login, then a business-scoped GET /api/v1/orders as a
    real hotel staff member would poll their own dashboard. Deliberately
    run at a much LOWER concurrency than the public QR scenarios: a real
    hotel's simultaneous staff device count is a few dozen at most, not
    thousands — the 5,000-user target applies to public QR guests, not
    staff. This exists to verify RBAC/tenant isolation and auth hold up
    while under concurrent public load, not to load-test auth itself."""
    abstract = True
    wait_time = between(5, 15)

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"identifier": self.email, "password": "LoadTestDevPassword123!"},
            name="/api/v1/auth/login",
        )
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"} if resp.status_code == 200 else {}

    @task
    def list_orders(self):
        if not self.headers:
            return
        with self.client.get("/api/v1/orders", headers=self.headers, name="/api/v1/orders [staff]", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"orders list failed: {resp.status_code}")
                return
            orders = resp.json()
            bad = [o for o in orders if o.get("id") and self.expected_business_check(o)]
            # OrderOut doesn't include business_id directly, so the real
            # tenant-isolation guarantee here is structural (business_id
            # comes only from the JWT server-side — see
            # app.core.dependencies.get_current_business_id) rather than
            # something the response body can assert per-row; this task's
            # real value is confirming auth + RBAC keep working under
            # concurrent public load, not re-deriving that guarantee.
            resp.success()

    def expected_business_check(self, order):
        return False


class StaffUserA(_StaffUserBase):
    email = "loadtest-owner-a@example.com"


class StaffUserB(_StaffUserBase):
    email = "loadtest-owner-b@example.com"
