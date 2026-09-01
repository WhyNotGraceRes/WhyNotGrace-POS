"""Photo-based menu digitization: platform staff upload menu-card photos,
review the AI-extracted draft, then publish it as real categories/items.
See app.services.menu_import_service and app.api.platform.menu_import.
"""
from app.services import menu_import_service
from tests.helpers import platform_login, register_and_login

A_TINY_JPEG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")


def _fake_extraction_response(categories: list[dict]):
    """Returns a fake replacement for menu_import_service's own `httpx`
    module reference (not the global httpx module) — swapping the global
    class would also intercept the TestClient's own requests, since
    FastAPI's TestClient is itself built on httpx.Client."""

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"content": [{"type": "tool_use", "name": "record_menu", "input": {"categories": categories}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeHttpx:
        Client = FakeClient

    return FakeHttpx()


def test_extract_returns_503_when_not_configured(client, db_session, monkeypatch):
    owner = register_and_login(client, db_session, business_name="Import Biz 1")
    platform_headers = platform_login(client, db_session)
    monkeypatch.setattr(menu_import_service.settings, "anthropic_api_key", "")

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/menu-import/extract",
        files=[("files", ("menu.jpg", A_TINY_JPEG, "image/jpeg"))],
        headers=platform_headers,
    )
    assert resp.status_code == 503


def test_extract_returns_structured_draft(client, db_session, monkeypatch):
    owner = register_and_login(client, db_session, business_name="Import Biz 2")
    platform_headers = platform_login(client, db_session)
    monkeypatch.setattr(menu_import_service.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(
        menu_import_service,
        "httpx",
        _fake_extraction_response(
            [
                {
                    "name": "Starters",
                    "items": [
                        {"name": "Paneer Tikka", "description": "Char-grilled", "price": 280, "is_veg": True},
                        {"name": "Chicken 65", "price": 320, "is_veg": False},
                    ],
                }
            ]
        ),
    )

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/menu-import/extract",
        files=[("files", ("menu.jpg", A_TINY_JPEG, "image/jpeg"))],
        headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["categories"]) == 1
    assert data["categories"][0]["name"] == "Starters"
    assert len(data["categories"][0]["items"]) == 2
    assert data["categories"][0]["items"][0]["price"] == 280.0


def test_extract_drops_items_with_no_price_or_name(client, db_session, monkeypatch):
    owner = register_and_login(client, db_session, business_name="Import Biz 3")
    platform_headers = platform_login(client, db_session)
    monkeypatch.setattr(menu_import_service.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(
        menu_import_service,
        "httpx",
        _fake_extraction_response(
            [
                {
                    "name": "Mains",
                    "items": [
                        {"name": "Dal Makhani", "price": 260, "is_veg": True},
                        {"name": "Unreadable smudge", "price": 0, "is_veg": True},
                        {"name": "", "price": 150, "is_veg": True},
                    ],
                }
            ]
        ),
    )

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/menu-import/extract",
        files=[("files", ("menu.jpg", A_TINY_JPEG, "image/jpeg"))],
        headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["categories"][0]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Dal Makhani"


def test_extract_rejects_unsupported_file_type(client, db_session, monkeypatch):
    owner = register_and_login(client, db_session, business_name="Import Biz 4")
    platform_headers = platform_login(client, db_session)
    monkeypatch.setattr(menu_import_service.settings, "anthropic_api_key", "test-key")

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/menu-import/extract",
        files=[("files", ("menu.pdf", b"%PDF-1.4", "application/pdf"))],
        headers=platform_headers,
    )
    assert resp.status_code == 400


def test_publish_creates_real_categories_and_items(client, db_session):
    owner = register_and_login(client, db_session, business_name="Import Biz 5")
    platform_headers = platform_login(client, db_session)

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/menu-import/publish",
        json={
            "categories": [
                {
                    "name": "Starters",
                    "items": [
                        {"name": "Paneer Tikka", "description": "Char-grilled", "price": 280, "is_veg": True},
                        {"name": "Chicken 65", "price": 320, "is_veg": False},
                    ],
                },
                {"name": "Mains", "items": [{"name": "Dal Makhani", "price": 260, "is_veg": True}]},
            ]
        },
        headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"categories_created": 2, "items_created": 3}

    categories = client.get("/api/v1/categories", headers=owner["headers"]).json()
    assert {c["name"] for c in categories} == {"Starters", "Mains"}

    items = client.get("/api/v1/menu/items", headers=owner["headers"]).json()
    assert {i["name"] for i in items} == {"Paneer Tikka", "Chicken 65", "Dal Makhani"}
    paneer = next(i for i in items if i["name"] == "Paneer Tikka")
    assert paneer["base_price"] == 280.0
    assert paneer["is_veg"] is True


def test_menu_import_endpoints_reject_a_business_token(client, db_session):
    owner = register_and_login(client, db_session, business_name="Import Biz 6")

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/menu-import/publish",
        json={"categories": []},
        headers=owner["headers"],
    )
    assert resp.status_code == 401
