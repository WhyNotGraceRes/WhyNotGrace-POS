from tests.helpers import create_category_and_item, create_table, enable_feature, register_and_login


def test_loyalty_rule_fires_reward_after_order_count_threshold(client, db_session):
    owner = register_and_login(client, db_session, business_name="Loyalty Biz 1")
    enable_feature(client, db_session, owner, "LOYALTY")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table = create_table(client, owner["headers"])

    resp = client.post(
        "/api/v1/customers", json={"first_name": "Rewards Fan", "mobile": "9000000099"}, headers=owner["headers"]
    )
    customer = resp.json()

    resp = client.post(
        "/api/v1/loyalty/rules",
        json={
            "name": "Every 2nd order free dessert", "rule_type": "ORDER_COUNT_THRESHOLD", "threshold": 2,
            "reward_type": "FREE_ITEM",
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201

    for _ in range(2):
        order_resp = client.post(
            "/api/v1/orders",
            json={
                "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
                "customer_id": customer["id"], "items": [{"menu_item_id": item["id"], "quantity": 1}],
            },
            headers=owner["headers"],
        )
        order = order_resp.json()
        bill = client.post(
            "/api/v1/billing/generate",
            json={"session_id": order["session_id"], "use_default_tax": False, "use_default_service_charge": False},
            headers=owner["headers"],
        ).json()
        client.post(
            "/api/v1/payments/cash", json={"bill_id": bill["id"], "amount": bill["grand_total"]}, headers=owner["headers"]
        )
        # each order+bill pair uses a fresh table visit
        table = create_table(client, owner["headers"])

    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["total_orders"] == 2

    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}/rewards", headers=owner["headers"])
    assert len(resp.json()) == 1


def test_review_requires_feature_flag(client, db_session):
    owner = register_and_login(client, db_session, business_name="Review Biz 1")
    slug = client.get("/api/v1/businesses/me", headers=owner["headers"]).json()["slug"]

    resp = client.post(
        f"/api/v1/reviews/public/{slug}",
        json={"first_name": "Diner", "mobile": "9111111111", "rating": 5, "comment": "Great!"},
    )
    assert resp.status_code == 403

    enable_feature(client, db_session, owner, "REVIEWS")
    resp = client.post(
        f"/api/v1/reviews/public/{slug}",
        json={"first_name": "Diner", "mobile": "9111111111", "rating": 5, "comment": "Great!"},
    )
    assert resp.status_code == 201
