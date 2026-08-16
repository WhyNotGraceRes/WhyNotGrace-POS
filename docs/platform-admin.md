# Platform admin: provisioning, entitlements, and managed billing

## Why this exists

The commercial model is a managed, tiered SaaS: WhyNotGrace staff provision
each client, decide what modules they're entitled to, and set what they're
charged — not self-checkout. That surface didn't exist. Worse, its absence
was an active commercial hole: `PUT /features/{module}` was gated only by
"are you the OWNER of your own business," so any restaurant owner could
self-enable every paid module — `QR_ORDERING`, `ONLINE_WEBSITE`, `DELIVERY`,
`ONLINE_PAYMENT` — for free. Closing that, and building the platform-staff
surface to replace it, is what this covers. Full design reasoning is in the
approved plan this was built from; this doc is the after-the-fact record of
what actually shipped and what's still open.

## What shipped

**A second, structurally separate principal.** `PlatformUser` /
`PlatformRefreshToken` are their own tables, not a nullable `business_id` on
the existing `User`. A platform JWT carries `"actor": "platform"` and
`business_id: None`; `get_current_user` (business path) explicitly rejects
that claim, and `get_current_platform_user` requires it — two dependency
chains that can never trust the same token. See
`backend/app/models/platform_user.py`'s docstring for the full reasoning.

**The entitlement hole is closed.** `PUT /features/{module}` no longer
exists on the business side at all (`GET` stays, read-only). The only writer
is `PUT /platform/businesses/{id}/features/{module}`, behind
`get_current_platform_user`. Verified live: a direct call to the old route
now 404s; the platform route works and the change is immediately visible to
the business.

**Entitlement toggles got their platform writer.** `owner_editable=False`
toggles were already correctly refused for owners
(`toggle_service.set_toggle`) — they just had no way to ever be *set*, since
nothing bypassed that gate. `toggle_service.platform_set_toggle` is that
path now, reusing the same row-upsert logic. No real toggle in the registry
is entitlement-class yet (every one shipped so far is owner-editable) — the
mechanism is proven end-to-end via tests, waiting for the first one.

**Self-registration is gone.** `POST /auth/register`,
`/auth/verify-email`, `/auth/resend-verification` and their schemas/service
functions were removed — a business only exists because
`POST /platform/businesses` created it, and the owner it creates is active
and pre-verified from the start (same precedent `POST /staff` already set
for staff created by an owner). `EmailVerificationCode` the model/table was
deliberately left in place rather than dropped — cheap to leave, and ripping
out a table is a bigger, separate decision than "stop exposing the route."

**Managed subscriptions replace self-checkout.** The old flat ₹699/month
Razorpay self-serve flow (`create_checkout`/`verify_checkout`) is retired.
Platform staff set `plan_name`/`amount`/`billing_interval`/`months` directly
via `POST /platform/businesses/{id}/subscription/provision`; actual payment
collection is offline/manual — this just records what was agreed.
`try_activate_by_provider_order_id` is kept as dormant plumbing so
`payment_service.py`'s shared Razorpay webhook dispatcher doesn't need
special-casing for anything still in flight from before this change.

**Grace period, then auto-suspend, confirmed with the client:**
`ACTIVE → GRACE` (0–3 days past `current_period_end`, dashboard still works,
banner shows) `→ SUSPENDED` (3+ days, dashboard login blocked). Computed
lazily on read (`subscription_service._apply_lazy_status`), same pattern as
the pre-existing `EXPIRED` transition — no scheduled job. `renew_plan` is
the *only* reactivation path: `base = max(now, current_period_end)` means
paying early never loses unused days, and paying from GRACE or SUSPENDED
starts fresh from today rather than stacking onto a lapsed date. Verified
live in the browser: suspending, confirming the dashboard blocks with a 402
and the red banner, then renewing and confirming the period end lands a
full month past the *original* end date (not from the renewal date), and
that the dashboard works again immediately.

**Enforcement is a single middleware, not a per-router dependency** —
`SubscriptionGateMiddleware` in `app/main.py`, so a new router can't forget
to include it. One real bug found only by browser testing (the backend test
suite's `TestClient` never would have caught it): the middleware was
originally registered *after* `CORSMiddleware`, making it outermost, so its
402 short-circuit bypassed CORS entirely — a real browser rejected the
response outright (`net::ERR_FAILED`, no status code visible to JS) instead
of seeing a clean 402. Fixed by registering it before `CORSMiddleware`. Worth
remembering: httpx-based tests don't enforce CORS at all, so this class of
bug is invisible to the test suite by construction — only a real browser
call proves it.

**`Business.is_active` now actually blocks the dashboard.** It already
gated public QR/website/reviews reads, but `get_current_business_id` — what
almost every authenticated business route actually depends on — read
`current_user.business_id` directly and never checked it. A platform admin
suspending a business via the kill-switch would not, on its own, have
blocked that business's staff at all. Fixed by routing
`get_current_business_id` through `get_current_business` (which does
check). This is the manual, immediate kill-switch (fraud/abuse/support),
deliberately separate from the billing-driven grace/suspend state machine
above.

**Frontend**: `/platform/*` is a route tree in the same app, not a second
deployable — its own Zustand store (`whynotgrace-platform-auth`
localStorage key, never touching the business `whynotgrace-auth` key), own
axios client with its own refresh interceptor, own shell
(`PlatformLayout`), no restaurant sidebar. `FeatureFlagsPage` is read-only
now; a `SubscriptionBanner` shows in the business dashboard for GRACE/
SUSPENDED.

## Explicitly not built (flagged on purpose)

- Automatic per-table QR fee (₹25/table/month) computation, or the one-time
  website-setup fee as its own billing line. `provision_plan` takes a flat
  `amount` platform staff type in — no per-table math yet.
- Any real online payment collection for managed plans. `renew_plan` is a
  manual "mark paid" action; money changes hands offline.
- The system rebrand (name pending from the client).
- A second platform role below `SUPERADMIN` (e.g. read-only support) — the
  `PlatformRole` enum and `require_platform_role` groundwork is there, just
  unused.

## Loose ends worth knowing about

**Two SubscriptionStatus values now do very similar jobs.** `EXPIRED` (the
original self-checkout lapse state) and `GRACE`/`SUSPENDED` (the new
managed-plan lifecycle) overlap in meaning. `EXPIRED` is still reachable —
`_apply_lazy_status` only escalates `ACTIVE`/`GRACE`, so a `Subscription`
row could in principle still carry stale legacy semantics if one existed
from before this change. Not a bug (nothing new writes `EXPIRED`), just
worth a cleanup pass if `EXPIRED` rows are confirmed to no longer exist
anywhere.

**`Business.is_active` and subscription `SUSPENDED` are two different
kill-switches with overlapping effect** (both end up blocking the
dashboard, via different mechanisms — one via `get_current_business_id`,
the other via the middleware). Deliberate, not accidental — see above — but
worth remembering they're not the same lever if a bug report ever says "I
reactivated their subscription and they're still locked out" (check
`is_active` too).

**`CANCELLED` does not block the dashboard.** Only `SUSPENDED` trips
`SubscriptionGateMiddleware`. A platform admin ending a business's plan
deliberately (not a billing lapse) currently has to *also* flip the
`is_active` kill-switch if they want that business fully cut off — cancelling
the plan alone leaves the dashboard working. Confirm this is the intended
behaviour before relying on it for an actual client offboarding.
