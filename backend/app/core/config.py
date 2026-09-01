"""Application configuration.

All configuration is sourced from environment variables (see .env.example).
No secrets are hardcoded. Production startup is rejected if insecure
development defaults are detected (see Settings.validate_production_safety).
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    app_name: str = "WhyNotGrace"
    api_v1_prefix: str = "/api/v1"

    # Database
    postgres_db: str = "whynotgrace"
    postgres_user: str = "whynotgrace"
    postgres_password: str = "changeme_dev_password"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None
    # Per-process SQLAlchemy pool. Defaults match the original single-worker
    # deployment's hardcoded values exactly, so existing single-worker
    # deployments are unaffected. When running with multiple uvicorn/gunicorn
    # workers, each worker creates its OWN pool of this size — set these so
    # that (workers x (db_pool_size + db_pool_max_overflow)) stays safely
    # under PostgreSQL's max_connections, with headroom for other clients
    # (psql, migrations, other services). See backend/README.md.
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20

    # Separate pool for the public QR endpoints (app/api/qr.py) ONLY —
    # everything else (staff dashboard, kitchen, orders, admin, auth, ...)
    # keeps using db_pool_size/db_pool_max_overflow above, on a completely
    # separate SQLAlchemy engine/connection pool. This means a QR-traffic
    # surge (thousands of guests scanning at once) that exhausts the QR
    # pool structurally CANNOT starve the staff dashboard of connections —
    # they draw from different pools, not just different pool "slots" of
    # the same one. Defaults mirror db_pool_size/db_pool_max_overflow for a
    # single default process; tune independently per backend/README.md's
    # pool-math section when running multiple workers.
    qr_db_pool_size: int = 10
    qr_db_pool_max_overflow: int = 20

    # Bounds how many QR requests may occupy a worker thread at once,
    # independent of anyio's process-wide default thread limiter (capacity
    # 40) that every other route — including the staff dashboard — still
    # uses. A real load test proved the separate QR DB pool above is NOT
    # enough on its own: FastAPI dispatches every sync route/dependency
    # (QR and staff alike) through that ONE shared default limiter, so QR
    # requests blocked on the QR DB pool were still occupying threads the
    # staff dashboard needed, producing 52s median dashboard latency with
    # zero DB errors. Giving QR its own CapacityLimiter (see
    # app/core/request_limits.py) means QR traffic can never consume more
    # than this many threads, no matter how overloaded it gets — the rest
    # of the process's default 40 threads stay available for staff/
    # dashboard/kitchen/orders/admin routes.
    qr_max_concurrent_requests: int = 30

    # Optional read-through cache for public, non-sensitive data (currently:
    # the QR public menu response — see app/core/cache.py). Unset by default,
    # which fully disables caching (every cache call becomes a no-op and the
    # app behaves exactly as it did before this existed). Never required for
    # correctness — only for reducing database load under concurrent read
    # traffic — so the app must keep working identically if this is unset or
    # if the configured Redis is unreachable.
    redis_url: str | None = None
    public_menu_cache_ttl_seconds: int = 60

    # Comma-separated IPs/CIDRs of reverse proxies allowed to set
    # X-Forwarded-For, or "*" to trust any peer (only safe when the app
    # publishes no port of its own and is reachable exclusively through the
    # proxy — which is exactly how docker-compose.prod.yml is built). Empty
    # (the default) means the header is ignored entirely and the direct peer
    # is used, exactly as before this setting existed.
    #
    # This matters more than it looks: every IP-keyed rate limit in
    # app/core/rate_limit.py reads its identity from here. Behind a proxy
    # with this unset, request.client.host is the proxy's own address on
    # every request, so each per-client limit silently becomes ONE GLOBAL
    # limit shared by the entire deployment. See app/core/client_ip.py.
    trusted_proxy_ips: str = ""

    # Responses at least this large are gzipped (see app/main.py). The QR
    # public menu is the reason this exists: it is the highest-traffic
    # response in the system, is served over restaurant WiFi and mobile
    # data, and is highly compressible JSON.
    gzip_minimum_size_bytes: int = 1000

    # Partner sales channels (a business's own website submitting orders —
    # see app/core/partner_auth.py). How far a signed request's timestamp may
    # be from server time before it is refused. This is the window in which a
    # captured request could be replayed if the nonce check somehow did not
    # apply, so it is deliberately short; it also bounds how long nonces need
    # to be retained. Too tight and ordinary clock drift on a partner's server
    # starts rejecting legitimate traffic — 300s is the usual compromise.
    partner_signature_max_skew_seconds: int = 300

    # JWT
    jwt_secret: str = INSECURE_DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 30

    # Login lockout
    login_max_attempts: int = 3
    login_lockout_minutes: int = 15

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Email
    email_backend: Literal["smtp", "console"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@whynotgrace.example"
    smtp_use_tls: bool = True

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Zomato
    zomato_api_base_url: str = ""
    zomato_client_id: str = ""
    zomato_client_secret: str = ""
    zomato_webhook_secret: str = ""

    # Swiggy
    swiggy_api_base_url: str = ""
    swiggy_client_id: str = ""
    swiggy_client_secret: str = ""
    swiggy_webhook_secret: str = ""

    # Anthropic (menu-photo digitization — see app/services/menu_import_service.py)
    anthropic_api_key: str = ""

    # QR
    qr_session_expire_hours: int = 6

    # Frontend
    frontend_base_url: str = "http://localhost:5173"

    @field_validator("database_url", mode="after")
    @classmethod
    def build_database_url(cls, v: str | None, info) -> str:
        if v:
            return v
        data = info.data
        return (
            f"postgresql+psycopg://{data.get('postgres_user')}:{data.get('postgres_password')}"
            f"@{data.get('postgres_host')}:{data.get('postgres_port')}/{data.get('postgres_db')}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_production_safety(self) -> None:
        """Refuse to boot in production with insecure defaults.

        This is called once at application startup (see app.main).
        """
        if not self.is_production:
            return

        errors: list[str] = []

        if self.jwt_secret == INSECURE_DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            errors.append(
                "JWT_SECRET is missing/insecure. Set a long random secret "
                "(e.g. `openssl rand -hex 64`) for production."
            )
        if self.debug:
            errors.append("DEBUG must be false in production.")
        if self.email_backend == "console":
            errors.append("EMAIL_BACKEND=console is not allowed in production; configure SMTP.")
        if not self.smtp_host and self.email_backend == "smtp":
            errors.append("SMTP_HOST is required when EMAIL_BACKEND=smtp.")
        if "changeme" in self.postgres_password.lower():
            errors.append("POSTGRES_PASSWORD looks like a development placeholder.")
        if not self.razorpay_key_id or not self.razorpay_key_secret:
            errors.append(
                "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are required in production "
                "to accept online payments."
            )
        if "*" in self.cors_origins_list:
            errors.append(
                "CORS_ORIGINS must not be '*' in production — allow_credentials=True "
                "combined with a wildcard origin would let any site make "
                "authenticated requests on a logged-in user's behalf. List the "
                "real frontend origin(s) explicitly (comma-separated)."
            )
        if not self.trusted_proxy_ips.strip():
            errors.append(
                "TRUSTED_PROXY_IPS must be set explicitly in production. The "
                "deployment guide puts a reverse proxy in front of this app, and "
                "when one is present but not declared here, every request appears "
                "to come from the proxy's own IP — which silently turns each "
                "per-client rate limit into a single GLOBAL limit shared by the "
                "whole deployment (e.g. 20 QR orders per minute across every "
                "business). Set it to the proxy's IP/CIDR, or to '*' if this app "
                "publishes no port of its own and is reachable only through the "
                "proxy (as in docker-compose.prod.yml). Set it to 'none' to "
                "state deliberately that this deployment is directly exposed "
                "with no proxy in front."
            )

        if errors:
            raise RuntimeError(
                "Refusing to start in production due to insecure configuration:\n- "
                + "\n- ".join(errors)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
