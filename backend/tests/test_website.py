"""The customer-facing website: platform staff paste in content (see
app.api.platform.website) and it becomes visible at a public, unauthenticated
URL keyed by business slug (see app.api.website's /public/* routes and
app.services.website_service.get_public_menu).
"""
from tests.helpers import (
    create_category_and_item,
    enable_feature,
    platform_login,
    register_and_login,
)


def _slug(client, platform_headers, business_id):
    resp = client.get(f"/api/v1/platform/businesses/{business_id}", headers=platform_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["slug"]


def _publish(client, platform_headers, business_id, **overrides):
    payload = {"is_published": True, "theme_color": "#1c1917"}
    payload.update(overrides)
    resp = client.put(
        f"/api/v1/platform/businesses/{business_id}/website", json=payload, headers=platform_headers
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_platform_can_read_and_write_website_config(client, db_session):
    owner = register_and_login(client, db_session, business_name="Website Biz 1")
    platform_headers = platform_login(client, db_session)

    resp = client.get(f"/api/v1/platform/businesses/{owner['business_id']}/website", headers=platform_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_published"] is False

    resp = client.put(
        f"/api/v1/platform/businesses/{owner['business_id']}/website",
        json={"logo_url": "https://cdn.example.com/logo.png", "story": "Est. 1998.", "theme_color": "#7c2d12"},
        headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["logo_url"] == "https://cdn.example.com/logo.png"
    assert data["story"] == "Est. 1998."
    assert data["theme_color"] == "#7c2d12"


def test_owner_cannot_reach_platform_website_endpoint(client, db_session):
    owner = register_and_login(client, db_session, business_name="Website Biz 2")

    resp = client.get(f"/api/v1/platform/businesses/{owner['business_id']}/website", headers=owner["headers"])
    assert resp.status_code == 401


def test_public_website_404s_until_module_enabled_and_published(client, db_session):
    owner = register_and_login(client, db_session, business_name="Website Biz 3")
    platform_headers = platform_login(client, db_session)
    slug = _slug(client, platform_headers, owner["business_id"])

    # Module off, nothing published yet.
    resp = client.get(f"/api/v1/website/public/{slug}")
    assert resp.status_code == 404

    enable_feature(client, db_session, owner, "ONLINE_WEBSITE")

    # Module is on but not published yet.
    resp = client.get(f"/api/v1/website/public/{slug}")
    assert resp.status_code == 404

    _publish(client, platform_headers, owner["business_id"])

    resp = client.get(f"/api/v1/website/public/{slug}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["business_name"] == owner["payload"]["business_name"]
    assert data["config"]["is_published"] is True
    assert data["config"]["theme_color"] == "#1c1917"


def test_public_website_unpublish_hides_it_again(client, db_session):
    owner = register_and_login(client, db_session, business_name="Website Biz 4")
    platform_headers = platform_login(client, db_session)
    slug = _slug(client, platform_headers, owner["business_id"])
    enable_feature(client, db_session, owner, "ONLINE_WEBSITE")
    _publish(client, platform_headers, owner["business_id"])

    resp = client.get(f"/api/v1/website/public/{slug}")
    assert resp.status_code == 200

    _publish(client, platform_headers, owner["business_id"], is_published=False)

    resp = client.get(f"/api/v1/website/public/{slug}")
    assert resp.status_code == 404


def test_public_website_menu_reflects_the_live_menu(client, db_session):
    owner = register_and_login(client, db_session, business_name="Website Biz 5")
    platform_headers = platform_login(client, db_session)
    slug = _slug(client, platform_headers, owner["business_id"])
    enable_feature(client, db_session, owner, "ONLINE_WEBSITE")
    _publish(client, platform_headers, owner["business_id"])

    _category, item = create_category_and_item(client, owner["headers"], price=350.0)

    resp = client.get(f"/api/v1/website/public/{slug}/menu")
    assert resp.status_code == 200, resp.text
    categories = resp.json()
    assert len(categories) == 1
    assert categories[0]["name"] == "Starters"
    assert len(categories[0]["items"]) == 1
    menu_item = categories[0]["items"][0]
    assert menu_item["id"] == item["id"]
    assert menu_item["price"] == 350.0


def test_public_website_menu_hides_sold_out_and_inactive_items(client, db_session):
    owner = register_and_login(client, db_session, business_name="Website Biz 6")
    platform_headers = platform_login(client, db_session)
    slug = _slug(client, platform_headers, owner["business_id"])
    enable_feature(client, db_session, owner, "ONLINE_WEBSITE")
    _publish(client, platform_headers, owner["business_id"])

    _category, item = create_category_and_item(client, owner["headers"], price=150.0)
    resp = client.put(
        f"/api/v1/menu/items/{item['id']}", json={"is_sold_out": True}, headers=owner["headers"]
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/api/v1/website/public/{slug}/menu")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_public_website_menu_404s_when_website_not_available(client, db_session):
    owner = register_and_login(client, db_session, business_name="Website Biz 7")
    platform_headers = platform_login(client, db_session)
    slug = _slug(client, platform_headers, owner["business_id"])

    resp = client.get(f"/api/v1/website/public/{slug}/menu")
    assert resp.status_code == 404
