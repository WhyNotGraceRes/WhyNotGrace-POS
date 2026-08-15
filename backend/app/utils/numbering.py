"""Human-readable sequence numbers for orders/KOTs/bills.

Not a strict monotonic sequence (no DB sequence contention across
tenants) — uniqueness comes from the UUID primary key; this is a display
convenience only.
"""
import secrets
from datetime import datetime, timezone


def generate_number(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    suffix = secrets.token_hex(2).upper()
    return f"{prefix}-{stamp}-{suffix}"
