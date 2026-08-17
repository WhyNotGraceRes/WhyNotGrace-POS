from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.helpers import create_category_and_item, create_table, register_and_login

IST = ZoneInfo("Asia/Kolkata")


def _place_order(client, headers, table, item):
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def test_dashboard_reflects_real_orders(client, db_session):
    owner = register_and_login(client, db_session, business_name="Dashboard Biz 1")
    _, item = create_category_and_item(client, owner["headers"], price=50)
    table = create_table(client, owner["headers"])

    resp = client.get("/api/v1/dashboard", headers=owner["headers"])
    assert resp.status_code == 200
    before = resp.json()["orders_today"]

    client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )

    resp = client.get("/api/v1/dashboard", headers=owner["headers"])
    assert resp.json()["orders_today"] == before + 1


def test_reports_channel_breakdown(client, db_session):
    owner = register_and_login(client, db_session, business_name="Dashboard Biz 2")
    _, item = create_category_and_item(client, owner["headers"], price=75)
    table = create_table(client, owner["headers"])

    client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )

    resp = client.get("/api/v1/reports/channels", headers=owner["headers"])
    assert resp.status_code == 200
    channels = {c["channel"]: c for c in resp.json()}
    assert channels["DINE_IN"]["order_count"] >= 1


def test_dashboard_payment_method_breakdown_matches_payments_today(client, db_session):
    """The breakdown must sum to payments_today_amount/count exactly — both
    are "today" on the same response, and they used to risk disagreeing if
    the breakdown reused reports_service's business-timezone "today"
    instead of this endpoint's own (see dashboard_service.py)."""
    owner = register_and_login(client, db_session, business_name="Dashboard Biz 5")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table = create_table(client, owner["headers"])

    order = _place_order(client, owner["headers"], table, item)
    resp = client.post(
        "/api/v1/billing/generate", json={"session_id": order["session_id"]}, headers=owner["headers"]
    )
    bill = resp.json()
    resp = client.post(
        "/api/v1/payments/cash",
        json={"bill_id": bill["id"], "amount": bill["grand_total"], "method": "CASH"},
        headers=owner["headers"],
    )
    assert resp.status_code == 201, resp.text

    resp = client.get("/api/v1/dashboard", headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()

    breakdown = body["payment_method_breakdown"]
    cash_row = next(r for r in breakdown if r["method"] == "CASH")
    assert cash_row["count"] >= 1
    assert cash_row["total_amount"] == bill["grand_total"]

    assert sum(r["count"] for r in breakdown) == body["payments_today_count"]
    assert sum(r["total_amount"] for r in breakdown) == body["payments_today_amount"]


def test_report_range_includes_its_final_day(client, db_session):
    """A range whose end is today must count today.

    The end date arrives as a calendar date and parses to midnight, so
    filtering `created_at <= end_date` excluded every order placed during the
    last day of the range — the Reports page showed zero for a range ending
    today while the Dashboard showed the real figure.
    """
    owner = register_and_login(client, db_session, business_name="Range Biz")
    _, item = create_category_and_item(client, owner["headers"], price=120)
    table = create_table(client, owner["headers"])
    _place_order(client, owner["headers"], table, item)

    today = datetime.now(IST).date().isoformat()
    params = {"start_date": today, "end_date": today}

    resp = client.get("/api/v1/reports/channels", params=params, headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    channels = {c["channel"]: c for c in resp.json()}
    assert channels["DINE_IN"]["order_count"] >= 1

    resp = client.get("/api/v1/reports/orders", params=params, headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    assert sum(r["order_count"] for r in resp.json()) >= 1

    resp = client.get("/api/v1/reports/top-items", params=params, headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    assert any(r["name"] == item["name"] for r in resp.json())


def test_report_range_ending_yesterday_excludes_today(client, db_session):
    """The other side of the boundary: widening the range must not swallow
    days that fall outside it."""
    owner = register_and_login(client, db_session, business_name="Range Biz 2")
    _, item = create_category_and_item(client, owner["headers"], price=120)
    table = create_table(client, owner["headers"])
    _place_order(client, owner["headers"], table, item)

    yesterday = (datetime.now(IST).date() - timedelta(days=1)).isoformat()
    resp = client.get(
        "/api/v1/reports/channels",
        params={"start_date": (datetime.now(IST).date() - timedelta(days=7)).isoformat(), "end_date": yesterday},
        headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text
    channels = {c["channel"]: c for c in resp.json()}
    assert channels.get("DINE_IN", {}).get("order_count", 0) == 0
