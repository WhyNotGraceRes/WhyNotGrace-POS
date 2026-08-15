def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_db(client):
    resp = client.get("/health/db")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_docs_enabled_outside_production(client):
    # Tests always run with APP_ENV=development (see conftest.py); this is
    # a regression guard for the docs_url=None-in-production conditional
    # in app.main — production's branch is covered by unit tests on
    # Settings itself (test_config_safety.py), since the app singleton
    # imported once at module scope can't be re-instantiated per-test.
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    resp = client.get("/docs")
    assert resp.status_code == 200
