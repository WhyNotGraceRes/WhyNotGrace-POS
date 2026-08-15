"""Covers the rate-limit identity fixes.

Two independent bugs are guarded here, both of which are silent in
development and only bite in production:

1. Behind a reverse proxy, request.client.host is the proxy's address on
   every request, so every per-client rate limit collapses into one global
   limit. app/core/client_ip.py fixes that — but only from proxies the
   deployment explicitly trusts, since X-Forwarded-For is otherwise
   attacker-controlled and trusting it blindly is worse than ignoring it.

2. Even with the real client IP, IP is the wrong identity for QR ordering:
   a venue's guests are all behind one NAT, so an IP-keyed limit caps the
   whole dining room at one guest's allowance.
"""
import uuid

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core import client_ip as client_ip_module
from app.core.client_ip import get_client_ip
from app.core.config import get_settings
from app.core.rate_limit import public_checkout_key, qr_location_key, qr_session_key


def _request(peer: str | None, headers: dict[str, str] | None = None, path_params: dict | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw,
        "client": (peer, 12345) if peer else None,
        "path_params": path_params or {},
    }
    req = Request(scope)
    assert isinstance(req.headers, Headers)
    return req


@pytest.fixture()
def trusted(monkeypatch):
    """Sets TRUSTED_PROXY_IPS and clears the module's parsed-config cache."""

    def _set(value: str):
        settings = get_settings()
        monkeypatch.setattr(settings, "trusted_proxy_ips", value, raising=False)
        client_ip_module.reset_for_tests()

    yield _set
    client_ip_module.reset_for_tests()


# --------------------------------------------------------------------------
# client IP resolution
# --------------------------------------------------------------------------

def test_forwarded_header_is_ignored_when_no_proxy_is_trusted(trusted):
    """The default. An untrusted caller must not be able to pick its own
    rate-limit bucket by sending a header."""
    trusted("")
    req = _request("203.0.113.9", {"X-Forwarded-For": "1.2.3.4"})
    assert get_client_ip(req) == "203.0.113.9"


def test_none_is_an_explicit_no_proxy_declaration(trusted):
    trusted("none")
    req = _request("203.0.113.9", {"X-Forwarded-For": "1.2.3.4"})
    assert get_client_ip(req) == "203.0.113.9"


def test_forwarded_header_is_honored_from_a_trusted_proxy(trusted):
    trusted("10.0.0.5")
    req = _request("10.0.0.5", {"X-Forwarded-For": "198.51.100.7"})
    assert get_client_ip(req) == "198.51.100.7"


def test_trusted_proxy_accepts_cidr_notation(trusted):
    trusted("10.0.0.0/8")
    req = _request("10.4.9.200", {"X-Forwarded-For": "198.51.100.7"})
    assert get_client_ip(req) == "198.51.100.7"


def test_wildcard_trusts_any_peer(trusted):
    trusted("*")
    req = _request("172.18.0.4", {"X-Forwarded-For": "198.51.100.7"})
    assert get_client_ip(req) == "198.51.100.7"


def test_wildcard_takes_the_leftmost_entry_of_a_chain(trusted):
    """Regression: under "*" every address matches the trusted check, so a
    naive rightmost-untrusted walk skips the whole chain and returns the
    proxy IP — reinstating the global-rate-limit bug. "*" is the value
    recommended for docker-compose.prod.yml, so this path must be right."""
    trusted("*")
    req = _request("172.18.0.4", {"X-Forwarded-For": "198.51.100.7, 172.18.0.9"})
    assert get_client_ip(req) == "198.51.100.7"


def test_spoofed_entries_left_of_our_proxies_are_not_believed(trusted):
    """The chain is `client, proxy1, proxy2`. Only entries our own trusted
    proxies appended can be believed, so resolution walks from the right and
    stops at the first address that isn't ours — a client that pre-seeds the
    header with a fake value cannot displace its real address."""
    trusted("10.0.0.0/8")
    req = _request("10.0.0.5", {"X-Forwarded-For": "1.1.1.1, 198.51.100.7, 10.0.0.9"})
    assert get_client_ip(req) == "198.51.100.7"


def test_garbage_in_the_header_falls_back_to_the_peer(trusted):
    trusted("10.0.0.5")
    req = _request("10.0.0.5", {"X-Forwarded-For": "not-an-ip"})
    assert get_client_ip(req) == "10.0.0.5"


def test_trusted_proxy_with_no_header_uses_the_peer(trusted):
    trusted("10.0.0.5")
    assert get_client_ip(_request("10.0.0.5")) == "10.0.0.5"


def test_missing_client_never_raises(trusted):
    trusted("*")
    assert get_client_ip(_request(None)) == "127.0.0.1"


# --------------------------------------------------------------------------
# key functions
# --------------------------------------------------------------------------

def test_qr_orders_are_keyed_per_session_not_per_ip():
    """The NAT case: two guests at different tables sharing the venue's one
    public IP must land in different buckets."""
    a = _request("203.0.113.9", {"X-QR-Session": "token-guest-a"})
    b = _request("203.0.113.9", {"X-QR-Session": "token-guest-b"})
    assert qr_session_key(a) != qr_session_key(b)
    assert qr_session_key(a) == "qr-session:token-guest-a"


def test_qr_session_key_falls_back_to_ip_when_header_absent(trusted):
    """A caller that omits the session header must still be limited."""
    trusted("none")
    assert qr_session_key(_request("203.0.113.9")) == "203.0.113.9"


def test_qr_scan_is_keyed_per_location():
    t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
    a = _request("203.0.113.9", path_params={"location_id": t1})
    b = _request("203.0.113.9", path_params={"location_id": t2})
    assert qr_location_key(a) != qr_location_key(b)
    assert qr_location_key(a) == f"qr-location:{t1}"


def test_checkout_key_is_scoped_per_business(trusted):
    """One busy tenant must not consume another tenant's budget."""
    trusted("none")
    a = _request("203.0.113.9", path_params={"business_slug": "biz-a"})
    b = _request("203.0.113.9", path_params={"business_slug": "biz-b"})
    assert public_checkout_key(a) != public_checkout_key(b)
    assert public_checkout_key(a) == "checkout:biz-a:203.0.113.9"


# --------------------------------------------------------------------------
# production safety
# --------------------------------------------------------------------------

def test_production_refuses_to_boot_without_a_declared_proxy_setting():
    """Silently defaulting here is exactly the bug: it degrades every
    per-client limit into a global one, with no error and no log line."""
    from app.core.config import Settings

    settings = Settings(
        app_env="production", debug=False, email_backend="smtp", smtp_host="smtp.example.com",
        jwt_secret="x" * 64, postgres_password="a-real-password",
        razorpay_key_id="rzp_live_x", razorpay_key_secret="secret",
        cors_origins="https://app.example.com", trusted_proxy_ips="",
    )
    with pytest.raises(RuntimeError, match="TRUSTED_PROXY_IPS"):
        settings.validate_production_safety()


def test_production_boots_once_the_proxy_setting_is_declared():
    from app.core.config import Settings

    settings = Settings(
        app_env="production", debug=False, email_backend="smtp", smtp_host="smtp.example.com",
        jwt_secret="x" * 64, postgres_password="a-real-password",
        razorpay_key_id="rzp_live_x", razorpay_key_secret="secret",
        cors_origins="https://app.example.com", trusted_proxy_ips="*",
    )
    settings.validate_production_safety()
