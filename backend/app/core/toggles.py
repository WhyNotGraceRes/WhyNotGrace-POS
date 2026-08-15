"""Fine-grained, per-business switches for individual behaviours.

This is deliberately a second mechanism alongside FeatureModule, not a
replacement, because the two answer different questions:

  FeatureModule  "does this business have QR ordering at all?"
                 Coarse, one row per product area, a Postgres enum, and
                 adding one costs a migration.
  Toggle         "does this counter require a reason when voiding a bill?"
                 Fine, dozens of them, defined in code, and adding one
                 costs nothing.

Putting these in FeatureModule would mean a migration per switch and would
conflate "what you bought" with "how you want it to behave".

THE IMPORTANT DISTINCTION: owner_editable
-----------------------------------------
Every toggle is one of two things, and confusing them breaks the commercial
model:

  PREFERENCE (owner_editable=True)
      How this restaurant wants to work. Round-off on or off, whether a void
      needs a manager. The owner is the right person to decide, and letting
      them decide costs nothing.

  ENTITLEMENT (owner_editable=False)
      What the business is entitled to under its plan. If an owner can flip
      their own entitlements, "pay only for the functions you need" collapses
      immediately — everyone turns everything on. So these are refused at the
      API layer for owners and can only be changed by the platform.

Both are enforced server-side. A disabled toggle must actually change what
the API does, never merely hide a button — the same rule
app/core/dependencies.py:require_feature already applies to modules.

**Known gap:** there is no platform-superadmin surface in this project yet
(see the backend README's feature-status matrix), so entitlement toggles
currently have no UI to change them and sit at their declared default. The
distinction is built in now so that entitlements are not accidentally
shipped as owner-editable and then have to be taken away later, which is a
far worse conversation to have with a paying client.
"""
import uuid
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session


class ToggleGroup(StrEnum):
    """Used to group switches on the settings screen."""
    BILLING = "BILLING"
    COUNTER = "COUNTER"


@dataclass(frozen=True)
class ToggleDef:
    key: str
    group: ToggleGroup
    default: bool
    owner_editable: bool
    # Shown on the settings screen. Kept here rather than in the frontend so
    # that a toggle cannot exist without an explanation of what turning it
    # off actually does.
    label: str
    description: str
    # Spelled out when the safe answer is not obvious, e.g. switches that
    # weaken an audit trail.
    warning: str | None = None


# Registry. Adding a switch is a one-line change here plus honouring it at
# the point of behaviour — no migration, no enum change.
_REGISTRY: dict[str, ToggleDef] = {}


def _register(toggle: ToggleDef) -> ToggleDef:
    if toggle.key in _REGISTRY:
        raise RuntimeError(f"Duplicate toggle key: {toggle.key}")
    _REGISTRY[toggle.key] = toggle
    return toggle


# --- Billing / invoice integrity -------------------------------------------

VOID_REQUIRES_REASON = _register(ToggleDef(
    key="billing.void_requires_reason",
    group=ToggleGroup.BILLING,
    default=True,
    owner_editable=True,
    label="Require a reason when voiding a bill",
    description="The cashier must type why the bill was cancelled. The reason is stored on the bill and in the audit log.",
    warning="Turning this off removes the only record of why bills were cancelled, which is the usual first sign of till fraud.",
))

VOID_REQUIRES_MANAGER = _register(ToggleDef(
    key="billing.void_requires_manager",
    group=ToggleGroup.BILLING,
    default=True,
    owner_editable=True,
    label="Only a manager or owner can void a bill",
    description="Cash counter staff cannot cancel a bill on their own.",
    warning="Turning this off lets any counter user cancel a bill they created, with nobody else involved.",
))

MARK_DUPLICATE_REPRINT = _register(ToggleDef(
    key="billing.mark_duplicate_reprint",
    group=ToggleGroup.BILLING,
    default=True,
    owner_editable=True,
    label="Mark reprinted bills as DUPLICATE",
    description="The first print is the original. Every print after it is marked, so two copies of one bill cannot both pass as the original.",
    warning="Turning this off makes a reprint indistinguishable from the original.",
))

INVOICE_SERIES_PER_YEAR = _register(ToggleDef(
    key="billing.invoice_series_per_year",
    group=ToggleGroup.BILLING,
    default=True,
    owner_editable=True,
    label="Restart invoice numbers each financial year",
    description="Numbering restarts at 1 on 1 April, with the financial year in the invoice number. This is what Indian GST expects.",
    warning="Turn this off only if your accountant has asked for one continuous series.",
))

ALLOW_REFUNDS = _register(ToggleDef(
    key="billing.allow_refunds",
    group=ToggleGroup.BILLING,
    default=True,
    owner_editable=True,
    label="Allow refunds against paid bills",
    description="Staff can refund a settled payment. The original payment and the refund both stay on record.",
))

ROUND_OFF_TOTAL = _register(ToggleDef(
    key="billing.round_off_total",
    group=ToggleGroup.BILLING,
    default=False,
    owner_editable=True,
    label="Round the bill total to the nearest rupee",
    description="Adds a round-off line so the guest pays a whole number. Off by default because it changes the amount charged.",
))


def all_toggles() -> list[ToggleDef]:
    return list(_REGISTRY.values())


def get_def(key: str) -> ToggleDef | None:
    return _REGISTRY.get(key)


def is_enabled(db: Session, business_id: uuid.UUID, toggle: ToggleDef) -> bool:
    """The single source of truth for whether a behaviour is on.

    Only stores overrides: a business with no row for a key gets the
    registry default. That means changing a default in code takes effect for
    every business that never expressed an opinion, which is what you want —
    and it keeps the table small instead of writing dozens of rows per
    business at signup.
    """
    from app.models.toggle import BusinessToggle

    row = (
        db.query(BusinessToggle)
        .filter(BusinessToggle.business_id == business_id, BusinessToggle.key == toggle.key)
        .first()
    )
    return toggle.default if row is None else row.enabled
