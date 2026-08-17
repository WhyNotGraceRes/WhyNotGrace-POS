"""Per-item/category name & description translations (hi/mr) — see
app.utils.i18n and the new /menu/items/{id}/translations,
/categories/{id}/translations endpoints. Exercises both the write side and
that a saved translation actually changes what a customer sees (the QR
menu, which reads through the same app.utils.i18n.translate() lookup as
the public website).
"""
from tests.helpers import create_category_and_item, create_table, enable_feature, register_and_login


def test_new_item_has_no_translations_yet(client, db_session):
    owner = register_and_login(client, db_session, business_name="Translate Biz 1")
    _category, item = create_category_and_item(client, owner["headers"])

    resp = client.get(f"/api/v1/menu/items/{item['id']}/translations", headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    rows = {row["language"]: row for row in resp.json()}
    assert set(rows) == {"hi", "mr"}
    assert rows["hi"]["name"] is None
    assert rows["hi"]["description"] is None


def test_set_and_read_back_an_item_translation(client, db_session):
    owner = register_and_login(client, db_session, business_name="Translate Biz 2")
    _category, item = create_category_and_item(client, owner["headers"])

    resp = client.put(
        f"/api/v1/menu/items/{item['id']}/translations/hi",
        json={"name": "पनीर टिक्का", "description": "मसाले में भुना पनीर"},
        headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"language": "hi", "name": "पनीर टिक्का", "description": "मसाले में भुना पनीर"}

    resp = client.get(f"/api/v1/menu/items/{item['id']}/translations", headers=owner["headers"])
    rows = {row["language"]: row for row in resp.json()}
    assert rows["hi"]["name"] == "पनीर टिक्का"
    assert rows["mr"]["name"] is None  # untouched


def test_clearing_a_translation_falls_back(client, db_session):
    owner = register_and_login(client, db_session, business_name="Translate Biz 3")
    _category, item = create_category_and_item(client, owner["headers"])

    client.put(
        f"/api/v1/menu/items/{item['id']}/translations/hi",
        json={"name": "पनीर टिक्का"},
        headers=owner["headers"],
    )
    resp = client.put(
        f"/api/v1/menu/items/{item['id']}/translations/hi",
        json={"name": ""},
        headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] is None


def test_unsupported_language_rejected(client, db_session):
    owner = register_and_login(client, db_session, business_name="Translate Biz 4")
    _category, item = create_category_and_item(client, owner["headers"])

    resp = client.put(
        f"/api/v1/menu/items/{item['id']}/translations/fr",
        json={"name": "Bonjour"},
        headers=owner["headers"],
    )
    assert resp.status_code == 400


def test_translation_endpoints_are_business_scoped(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="Translate Biz 5a")
    owner_b = register_and_login(client, db_session, business_name="Translate Biz 5b")
    _category, item = create_category_and_item(client, owner_a["headers"])

    resp = client.get(f"/api/v1/menu/items/{item['id']}/translations", headers=owner_b["headers"])
    assert resp.status_code == 404

    resp = client.put(
        f"/api/v1/menu/items/{item['id']}/translations/hi", json={"name": "x"}, headers=owner_b["headers"]
    )
    assert resp.status_code == 404


def test_category_translation_round_trip(client, db_session):
    owner = register_and_login(client, db_session, business_name="Translate Biz 6")
    category, _item = create_category_and_item(client, owner["headers"])

    resp = client.put(
        f"/api/v1/categories/{category['id']}/translations/mr",
        json={"name": "स्टार्टर्स"},
        headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"language": "mr", "name": "स्टार्टर्स", "description": None}

    resp = client.get(f"/api/v1/categories/{category['id']}/translations", headers=owner["headers"])
    rows = {row["language"]: row for row in resp.json()}
    assert rows["mr"]["name"] == "स्टार्टर्स"


def test_translated_name_appears_in_the_qr_menu(client, db_session):
    owner = register_and_login(client, db_session, business_name="Translate Biz 7")
    enable_feature(client, db_session, owner, "QR_ORDERING")
    category, item = create_category_and_item(client, owner["headers"], price=120)
    table = create_table(client, owner["headers"], name="Q1")

    client.put(
        f"/api/v1/menu/items/{item['id']}/translations/hi",
        json={"name": "पनीर टिक्का", "description": "मसाले में भुना पनीर"},
        headers=owner["headers"],
    )
    client.put(
        f"/api/v1/categories/{category['id']}/translations/hi",
        json={"name": "स्टार्टर"},
        headers=owner["headers"],
    )

    slug = client.get("/api/v1/businesses/me", headers=owner["headers"]).json()["slug"]
    locations = client.get("/api/v1/locations", headers=owner["headers"]).json()
    location = next(l for l in locations if l["id"] == table["id"])
    qr_code = location["qr_url"].split("c=")[1]
    session_token = client.get(
        f"/api/v1/qr/scan/{slug}/{table['id']}", params={"c": qr_code}
    ).json()["session_token"]

    # English by default — untouched fallback.
    resp = client.get("/api/v1/qr/menu", headers={"X-QR-Session": session_token})
    assert resp.json()["categories"][0]["items"][0]["name"] == item["name"]

    # Hindi picks up what was just saved.
    resp = client.get("/api/v1/qr/menu", params={"lang": "hi"}, headers={"X-QR-Session": session_token})
    assert resp.status_code == 200, resp.text
    translated_category = resp.json()["categories"][0]
    assert translated_category["name"] == "स्टार्टर"
    translated_item = translated_category["items"][0]
    assert translated_item["name"] == "पनीर टिक्का"
    assert translated_item["description"] == "मसाले में भुना पनीर"

    # Marathi was never set for this item — falls back to English.
    resp = client.get("/api/v1/qr/menu", params={"lang": "mr"}, headers={"X-QR-Session": session_token})
    assert resp.json()["categories"][0]["items"][0]["name"] == item["name"]
