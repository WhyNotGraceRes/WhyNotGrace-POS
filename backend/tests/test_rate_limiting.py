"""Verifies the slowapi-based rate limiter (app/core/rate_limit.py) is
actually wired up and enforced — not just present in source. Uses a low,
easy-to-exceed-deterministically limit test (login: 10/minute) rather than
sleeping for real time windows.
"""
from app.core.rate_limit import limiter
from tests.helpers import register_and_login


def test_login_is_rate_limited_after_repeated_requests(client, db_session):
    owner = register_and_login(client, db_session, business_name="Rate Limit Biz 1")

    # login is capped at 10/minute per IP; TestClient requests all share one
    # address, so the 11th rapid attempt must be throttled regardless of
    # whether the credentials are even correct.
    last_status = None
    for _ in range(11):
        resp = client.post(
            "/api/v1/auth/login",
            json={"identifier": owner["payload"]["email"], "password": "wrong-on-purpose"},
        )
        last_status = resp.status_code

    assert last_status == 429


def test_rate_limit_response_does_not_leak_internals(client, db_session):
    owner = register_and_login(client, db_session, business_name="Rate Limit Biz 2")

    for _ in range(11):
        resp = client.post(
            "/api/v1/auth/login",
            json={"identifier": owner["payload"]["email"], "password": "wrong-on-purpose"},
        )
    assert resp.status_code == 429
    body = resp.json()
    # slowapi's default handler returns a plain rate-limit message — must
    # never include a stack trace or internal exception representation.
    assert "traceback" not in str(body).lower()
    assert "Traceback" not in str(body)


def test_platform_login_endpoint_is_rate_limited(client):
    """There is no self-registration any more (see app.api.auth) — platform
    login is the entry point that most needs this protection now, since a
    platform account can touch every tenant."""
    statuses = []
    for _ in range(11):
        resp = client.post(
            "/api/v1/platform/auth/login", json={"email": "nobody@example.com", "password": "wrong-on-purpose"}
        )
        statuses.append(resp.status_code)

    assert statuses[-1] == 429


def test_account_lockout_still_works_independently_of_ip_rate_limit(client, db_session):
    """Phase 7's account-level lockout (3 wrong attempts -> 423) must still
    fire before the new IP-level limiter (10/minute) would even kick in —
    the two layers are independent and this one must not have regressed.
    """
    owner = register_and_login(client, db_session, business_name="Rate Limit Biz 3")

    for _ in range(2):
        resp = client.post(
            "/api/v1/auth/login",
            json={"identifier": owner["payload"]["email"], "password": "wrong-password"},
        )
        assert resp.status_code == 401

    resp = client.post(
        "/api/v1/auth/login", json={"identifier": owner["payload"]["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 423


def test_limiter_reset_between_tests_via_client_fixture(client):
    """Sanity check for the conftest.py fixture change itself: a fresh
    `client` in a new test must start with a clean rate-limit counter, not
    inherit exhaustion from whichever test ran before it in the session.
    """
    resp = client.post(
        "/api/v1/auth/login", json={"identifier": "nobody@example.com", "password": "whatever"}
    )
    assert resp.status_code != 429
