"""SQLAlchemy engine/session factory. PostgreSQL only — no SQLite fallback."""
import logging
import os
import time
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

if not settings.database_url.startswith("postgresql"):
    raise RuntimeError(
        "DATABASE_URL must be a PostgreSQL connection string. "
        "SQLite and other engines are not supported by this application."
    )

# prepare_threshold=None disables psycopg3's server-side prepared-statement
# cache. Required for correctness when DATABASE_URL points at PgBouncer in
# transaction-pooling mode (see backend/deploy/pgbouncer/pgbouncer.ini):
# a prepared statement lives on one real Postgres backend connection, but
# transaction pooling can hand a client a DIFFERENT real connection on its
# very next query, producing "prepared statement ... does not exist"
# errors. Harmless and has no measurable cost against direct Postgres too,
# so it's set unconditionally rather than gated behind an env var.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_pool_max_overflow,
    connect_args={"prepare_threshold": None},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)

# Separate engine/pool for the public QR endpoints only (see get_qr_db()
# below and app/api/qr.py) — deliberately a second, independent connection
# pool to the SAME database, not a shared one. A surge of public QR/guest
# traffic that exhausts this pool cannot, even in principle, prevent the
# staff dashboard/kitchen/orders/admin routes (which all still use `engine`
# above) from getting their own connections — they are structurally
# different pools. See backend/README.md's "Scaling beyond one process"
# section for the connection-count math across both pools.
qr_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.qr_db_pool_size,
    max_overflow=settings.qr_db_pool_max_overflow,
    connect_args={"prepare_threshold": None},
    future=True,
)
QRSessionLocal = sessionmaker(bind=qr_engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)

# Generic public-menu cache invalidation: rather than hand-adding a
# cache.invalidate_business_menu() call to every menu/category/item/variant/
# option/price-rule mutation endpoint individually (15+ routes across
# app/api/menu.py, categories.py, pricing.py — easy to miss one), this pair
# of session-commit hooks watches every write against the base ORM Session
# class (i.e. every session created via SessionLocal, app-wide) and
# invalidates the affected business's cache once the transaction that
# touched a menu-related table actually commits. If caching is disabled
# (no REDIS_URL) this is a no-op — see app/core/cache.py.
_MENU_CACHE_TABLES = {"menu_categories", "menu_items", "menu_variants", "menu_option_groups", "menu_options", "price_rules"}


@event.listens_for(Session, "before_commit")
def _capture_menu_cache_invalidation(session: Session) -> None:
    changed_business_ids = {
        obj.business_id
        for obj in (*session.new, *session.dirty, *session.deleted)
        if getattr(obj, "__tablename__", None) in _MENU_CACHE_TABLES and getattr(obj, "business_id", None) is not None
    }
    if changed_business_ids:
        session.info["_menu_cache_invalidate"] = changed_business_ids


@event.listens_for(Session, "after_commit")
def _invalidate_menu_cache_after_commit(session: Session) -> None:
    business_ids = session.info.pop("_menu_cache_invalidate", None)
    if not business_ids:
        return
    from app.core import cache

    for business_id in business_ids:
        cache.invalidate_business_menu(business_id)

# Opt-in, zero-cost-when-disabled per-query timing, used to diagnose
# connection-pool exhaustion under load (distinguishing "queries are slow"
# from "queries are fast but the process is too busy to run them promptly").
# Off by default in every environment, including production — set
# SQL_QUERY_PROFILING=1 only for a diagnostic run. See backend/loadtest/README.md.
if os.getenv("SQL_QUERY_PROFILING") == "1":
    _slow_query_log = logging.getLogger("sql_profiling")
    _SLOW_QUERY_THRESHOLD_MS = 50

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._profiling_start = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        duration_ms = (time.perf_counter() - context._profiling_start) * 1000
        if duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _slow_query_log.warning("SLOW QUERY %.1fms: %s", duration_ms, statement[:200])


# Opt-in pool-lifecycle instrumentation, off by default. Set
# SQL_POOL_PROFILING=1 to log every checkout/checkin/connect/close/invalidate
# on the pool, plus every get_db() generator open/close, tagged with the
# worker's PID and each Session's id() — used to prove (not guess) whether
# every connection checked out during a request is actually returned to the
# pool, and whether get_db()'s own `finally` runs for every request it
# starts. See backend/loadtest/README.md.
if os.getenv("SQL_POOL_PROFILING") == "1":
    _pool_log = logging.getLogger("pool_profiling")
    _pid = os.getpid()

    @event.listens_for(engine, "checkout")
    def _on_checkout(dbapi_conn, connection_record, connection_proxy):
        _pool_log.warning("POOL CHECKOUT pid=%s conn=%s", _pid, id(dbapi_conn))

    @event.listens_for(engine, "checkin")
    def _on_checkin(dbapi_conn, connection_record):
        _pool_log.warning("POOL CHECKIN  pid=%s conn=%s", _pid, id(dbapi_conn))

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, connection_record):
        _pool_log.warning("POOL CONNECT  pid=%s conn=%s", _pid, id(dbapi_conn))

    @event.listens_for(engine, "close")
    def _on_close(dbapi_conn, connection_record):
        _pool_log.warning("POOL CLOSE    pid=%s conn=%s", _pid, id(dbapi_conn))

    @event.listens_for(engine, "invalidate")
    def _on_invalidate(dbapi_conn, connection_record, exception):
        _pool_log.warning("POOL INVALIDATE pid=%s conn=%s exc=%r", _pid, id(dbapi_conn), exception)

    # Same instrumentation, same env var, on the separate QR pool — tagged
    # "qr_pool=1" in the log line so the two pools' checkout/checkin
    # activity can be told apart during a diagnostic run.
    @event.listens_for(qr_engine, "checkout")
    def _on_qr_checkout(dbapi_conn, connection_record, connection_proxy):
        _pool_log.warning("POOL CHECKOUT pid=%s conn=%s qr_pool=1", _pid, id(dbapi_conn))

    @event.listens_for(qr_engine, "checkin")
    def _on_qr_checkin(dbapi_conn, connection_record):
        _pool_log.warning("POOL CHECKIN  pid=%s conn=%s qr_pool=1", _pid, id(dbapi_conn))

    @event.listens_for(qr_engine, "connect")
    def _on_qr_connect(dbapi_conn, connection_record):
        _pool_log.warning("POOL CONNECT  pid=%s conn=%s qr_pool=1", _pid, id(dbapi_conn))

    @event.listens_for(qr_engine, "close")
    def _on_qr_close(dbapi_conn, connection_record):
        _pool_log.warning("POOL CLOSE    pid=%s conn=%s qr_pool=1", _pid, id(dbapi_conn))

    @event.listens_for(qr_engine, "invalidate")
    def _on_qr_invalidate(dbapi_conn, connection_record, exception):
        _pool_log.warning("POOL INVALIDATE pid=%s conn=%s qr_pool=1 exc=%r", _pid, id(dbapi_conn), exception)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    if os.getenv("SQL_POOL_PROFILING") == "1":
        logging.getLogger("pool_profiling").warning("SESSION OPEN  pid=%s session=%s", os.getpid(), id(db))
    try:
        yield db
    finally:
        if os.getenv("SQL_POOL_PROFILING") == "1":
            logging.getLogger("pool_profiling").warning("SESSION CLOSE pid=%s session=%s", os.getpid(), id(db))
        db.close()


def get_qr_db() -> Generator[Session, None, None]:
    """Identical lifecycle to get_db() above, bound to the separate
    qr_engine/QRSessionLocal — used ONLY by app/api/qr.py's public
    endpoints, so QR traffic never draws from the same connection pool as
    the staff dashboard/kitchen/orders/admin routes."""
    db = QRSessionLocal()
    if os.getenv("SQL_POOL_PROFILING") == "1":
        logging.getLogger("pool_profiling").warning("SESSION OPEN  pid=%s session=%s qr_pool=1", os.getpid(), id(db))
    try:
        yield db
    finally:
        if os.getenv("SQL_POOL_PROFILING") == "1":
            logging.getLogger("pool_profiling").warning("SESSION CLOSE pid=%s session=%s qr_pool=1", os.getpid(), id(db))
        db.close()
