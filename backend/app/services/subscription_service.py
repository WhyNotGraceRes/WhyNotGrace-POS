"""A business's own subscription to the WhyNotGrace platform.

This used to be flat self-serve checkout (₹699/month via the platform's
global Razorpay). It is now platform-managed: WhyNotGrace staff decide the
plan and price per client and provision/renew it directly (see
app.api.platform.subscriptions) — there is no self-checkout any more, and
no single default plan, so PLAN_NAME/PLAN_AMOUNT-style constants that used
to live here are gone along with the checkout/verify functions that read
them.

try_activate_by_provider_order_id and _activate_from_payment are kept
dormant: app.services.payment_service's shared Razorpay webhook dispatcher
still calls the former to check whether an incoming payment belongs to a
(now-unreachable-in-practice) legacy SubscriptionPayment before concluding
it's not a restaurant-bill payment either. Nothing can create a new
SubscriptionPayment any more, so this path only matters for anything still
in flight from before this change, and costs nothing to leave as a no-op
once those clear.
"""
import calendar
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import PaymentStatus, SubscriptionStatus
from app.models.subscription import Subscription, SubscriptionPayment

DEFAULT_CURRENCY = "INR"

# How long a lapsed plan keeps working (with a warning) before it's
# suspended. Confirmed with the client: 3 days from current_period_end,
# then blocked until platform staff renews — see renew_plan for why
# renewing is also the only reactivation path.
GRACE_PERIOD_DAYS = 3


def _add_months(dt: datetime, months: int) -> datetime:
    """Calendar-month add with end-of-month clamping (Jan 31 + 1 -> Feb
    28/29), stdlib only.
    """
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _get_subscription_row(db: Session, business_id: uuid.UUID) -> Subscription | None:
    return db.query(Subscription).filter(Subscription.business_id == business_id).first()


def _get_subscription_or_404(db: Session, business_id: uuid.UUID) -> Subscription:
    subscription = _get_subscription_row(db, business_id)
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription for this business yet")
    return subscription


def _apply_lazy_status(subscription: Subscription) -> None:
    """ACTIVE -> GRACE -> SUSPENDED, applied lazily on read — there is no
    background job in this deployment to sweep for lapses. Mutates in
    place; caller flushes.

    Runs for ACTIVE *and* GRACE (not just ACTIVE) so a subscription already
    sitting in GRACE keeps getting re-evaluated on each read and can still
    escalate to SUSPENDED once the grace window passes — the single-shot
    "only from ACTIVE" version of this check would freeze at GRACE forever.
    """
    if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE):
        return
    if subscription.current_period_end is None:
        return

    now = datetime.now(timezone.utc)
    grace_deadline = subscription.current_period_end + timedelta(days=GRACE_PERIOD_DAYS)

    if now > grace_deadline:
        subscription.status = SubscriptionStatus.SUSPENDED
    elif now > subscription.current_period_end:
        subscription.status = SubscriptionStatus.GRACE


def get_subscription(db: Session, business_id: uuid.UUID) -> Subscription | None:
    subscription = _get_subscription_row(db, business_id)
    if subscription is not None:
        _apply_lazy_status(subscription)
        db.flush()
    return subscription


def provision_plan(
    db: Session, business_id: uuid.UUID, *, plan_name: str, amount: float, billing_interval: str, months: int,
    platform_user_id: uuid.UUID,
) -> Subscription:
    """Sets (or replaces) a business's plan and starts a fresh period from
    now. Distinct from renew_plan: this is for a new plan or changing an
    existing one's terms, not extending the current one — see renew_plan
    for why a mid-cycle change should go through provision, not renew.
    """
    subscription = _get_subscription_row(db, business_id)
    now = datetime.now(timezone.utc)
    period_end = _add_months(now, months)

    if subscription is None:
        subscription = Subscription(
            business_id=business_id, plan_name=plan_name, amount=amount, currency=DEFAULT_CURRENCY,
            billing_interval=billing_interval, status=SubscriptionStatus.ACTIVE,
            current_period_start=now, current_period_end=period_end,
        )
        db.add(subscription)
    else:
        subscription.plan_name = plan_name
        subscription.amount = amount
        subscription.currency = DEFAULT_CURRENCY
        subscription.billing_interval = billing_interval
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = now
        subscription.current_period_end = period_end
        subscription.cancelled_at = None
    db.flush()
    return subscription


def renew_plan(db: Session, business_id: uuid.UUID, *, months: int, platform_user_id: uuid.UUID) -> Subscription:
    """Extends the current plan and is the only reactivation path — there
    is no separate "un-suspend" action.

    base = max(now, current_period_end) so paying early never loses the
    unused remainder of the current period, and paying late (from GRACE or
    already SUSPENDED) simply starts the new period from today rather than
    stacking it after a lapsed end date. One formula covers on-time
    renewal, early renewal, and reactivation-after-suspension — confirmed
    with the client as the intended behaviour ("days will be added to
    existing remaining days").
    """
    subscription = _get_subscription_or_404(db, business_id)
    now = datetime.now(timezone.utc)
    base = subscription.current_period_end if subscription.current_period_end and subscription.current_period_end > now else now

    if subscription.current_period_start is None:
        subscription.current_period_start = now
    subscription.current_period_end = _add_months(base, months)
    subscription.status = SubscriptionStatus.ACTIVE
    db.flush()
    return subscription


def suspend_plan(db: Session, business_id: uuid.UUID, *, platform_user_id: uuid.UUID) -> Subscription:
    """A manual override for support/fraud cases — immediate, not tied to
    the grace-period math. renew_plan is still the only way back in.
    """
    subscription = _get_subscription_or_404(db, business_id)
    subscription.status = SubscriptionStatus.SUSPENDED
    db.flush()
    return subscription


def cancel_plan(db: Session, business_id: uuid.UUID, *, platform_user_id: uuid.UUID) -> Subscription:
    """Ends the relationship deliberately — distinct from SUSPENDED, which
    is a billing lapse the business can still resolve by paying.
    """
    subscription = _get_subscription_or_404(db, business_id)
    if subscription.status != SubscriptionStatus.CANCELLED:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(timezone.utc)
        db.flush()
    return subscription


def _activate_from_payment(db: Session, payment: SubscriptionPayment) -> None:
    payment.status = PaymentStatus.SUCCESS
    payment.verified_at = datetime.now(timezone.utc)
    db.flush()

    subscription = db.get(Subscription, payment.subscription_id)
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.current_period_start = payment.period_start
    subscription.current_period_end = payment.period_end
    db.flush()


def try_activate_by_provider_order_id(
    db: Session, provider_order_id: str, business_id: uuid.UUID | None, provider_payment_id: str | None
) -> SubscriptionPayment | None:
    """See the module docstring: dormant now that nothing creates new
    SubscriptionPayment rows, kept only so the shared webhook dispatcher in
    payment_service.py doesn't need special-casing for something that may
    still be in flight from before this change.
    """
    query = db.query(SubscriptionPayment).filter(SubscriptionPayment.provider_order_id == provider_order_id)
    if business_id is not None:
        query = query.filter(SubscriptionPayment.business_id == business_id)
    payment = query.first()
    if payment is None or payment.status == PaymentStatus.SUCCESS:
        return None
    payment.provider_payment_id = provider_payment_id
    _activate_from_payment(db, payment)
    return payment
