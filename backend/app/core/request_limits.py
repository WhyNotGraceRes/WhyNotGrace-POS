"""Process-wide request-concurrency limiter for the public QR endpoints.

See app/core/config.py's qr_max_concurrent_requests for why this exists: a
separate DB connection pool (app/database/session.py's qr_engine) was not
enough by itself to protect the staff dashboard from a QR traffic surge,
because Starlette/FastAPI dispatch every sync route and sync dependency
through ONE shared anyio thread limiter (default capacity 40, process-wide)
regardless of which DB engine the route uses. app/api/qr.py's routes run
their blocking work through THIS limiter instead of the default one, so QR
traffic can never occupy more than qr_max_concurrent_requests worker
threads — the rest of the process's default-limiter threads remain
available for every other (staff/dashboard/kitchen/orders/admin) route.
"""
import anyio

from app.core.config import get_settings

settings = get_settings()

qr_thread_limiter = anyio.CapacityLimiter(settings.qr_max_concurrent_requests)
