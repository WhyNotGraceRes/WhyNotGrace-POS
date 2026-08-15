"""Resolving the real client IP behind a reverse proxy, safely.

`request.client.host` is the IP of whatever opened the TCP connection. In
the production topology (see docker-compose.prod.yml) that is always the
`lb` nginx container, never the guest's phone — so every request in the
entire deployment carries an identical client IP. Anything keyed off it
(most importantly app/core/rate_limit.py) therefore stops being a
per-client limit and silently becomes a single GLOBAL limit shared by every
user of every business.

The fix is to read the real client IP out of `X-Forwarded-For`, which
`deploy/nginx/nginx.conf` already sets. But that header is attacker-
controlled: anyone who can reach the app directly can send
`X-Forwarded-For: <random>` on every request and get a fresh rate-limit
bucket each time, which is strictly worse than not reading it at all.

So the header is honored ONLY when the immediate peer — the machine that
actually opened the connection — is a configured trusted proxy
(TRUSTED_PROXY_IPS). Default is empty: no proxy is trusted, the header is
ignored entirely, and behavior is byte-for-byte identical to before this
module existed. A deployment behind a proxy must opt in explicitly.

Which entry of X-Forwarded-For to use: the header is a chain,
`client, proxy1, proxy2, ...`, appended to by each hop. Only the entries
added by our own trusted proxies can be believed; everything to the left
may have been forged by the client. So we walk the chain from the right,
skipping trusted-proxy addresses, and take the first untrusted one — that
is the closest address our infrastructure actually observed.
"""
import ipaddress
import logging
from functools import lru_cache

from starlette.requests import Request

from app.core.config import get_settings

logger = logging.getLogger("client_ip")

_FALLBACK_IP = "127.0.0.1"


@lru_cache(maxsize=1)
def _trusted_networks() -> tuple[bool, tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]]:
    """Returns (trust_any, networks). Parsed once — this runs on every
    rate-limited request, so it must not re-parse configuration each time.
    """
    raw = get_settings().trusted_proxy_ips.strip()
    # "none" is the explicit form of "no proxy in front of this deployment",
    # accepted so production can satisfy validate_production_safety()'s
    # requirement that this be a deliberate choice rather than an oversight.
    if not raw or raw.lower() == "none":
        return False, ()
    if raw == "*":
        # Only safe when the app is genuinely unreachable except through the
        # proxy — which is exactly the case in docker-compose.prod.yml, where
        # the backend publishes no host port at all and lives on an internal
        # compose network. Documented in .env.production.example.
        return True, ()

    networks = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            # strict=False so a plain host address ("10.0.0.7") and a CIDR
            # block ("10.0.0.0/8") are both accepted.
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Ignoring unparseable TRUSTED_PROXY_IPS entry: %r", entry)
    return False, tuple(networks)


def _is_trusted(ip: str) -> bool:
    trust_any, networks = _trusted_networks()
    if trust_any:
        return True
    if not networks:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def get_client_ip(request: Request) -> str:
    """The best available identity for "who sent this request".

    Falls back to the direct peer whenever the header is absent, malformed,
    or the peer is not a trusted proxy — never raises, since it is called
    from the rate limiter on the hot path.
    """
    peer = request.client.host if request.client else None
    if not peer:
        return _FALLBACK_IP
    if not _is_trusted(peer):
        return peer

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        # Trusted proxy that didn't set the header — nothing better to use.
        return peer

    entries = [p.strip() for p in forwarded.split(",") if p.strip()]
    trust_any, _ = _trusted_networks()

    if trust_any:
        # Under "*" every address matches _is_trusted, so the rightmost-
        # untrusted walk below would skip the entire chain and fall back to
        # the proxy IP — silently reinstating the very bug this module
        # exists to fix. "*" means "I cannot enumerate my proxies, but the
        # app is only reachable through them", so the leftmost entry (the
        # original client) is the honest answer. This matches uvicorn's own
        # --forwarded-allow-ips='*' semantics.
        for candidate in entries:
            try:
                ipaddress.ip_address(candidate)
            except ValueError:
                break
            return candidate
        return peer

    # Rightmost-untrusted wins: entries appended by our own proxies are the
    # only ones we can believe, so skip them and take the first address that
    # isn't one of ours.
    for candidate in reversed(entries):
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            # A forged/garbage entry. Everything further left is at least as
            # untrustworthy, so stop rather than keep walking.
            break
        if not _is_trusted(candidate):
            return candidate

    # Every hop in the chain was a trusted proxy of ours; the peer is as
    # specific as we can honestly get.
    return peer


def reset_for_tests() -> None:
    """Test-only: clears the parsed-config cache after monkeypatching
    settings.trusted_proxy_ips."""
    _trusted_networks.cache_clear()
