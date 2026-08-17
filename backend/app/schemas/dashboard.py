import uuid

from pydantic import BaseModel


class TopMenuItemOut(BaseModel):
    menu_item_id: uuid.UUID
    name: str
    quantity_sold: int


class PaymentMethodBreakdownOut(BaseModel):
    method: str
    count: int
    total_amount: float


class DashboardResponse(BaseModel):
    sales_today: float
    orders_today: int
    pending_orders: int
    kot_queue: int
    ready_orders: int
    tables_occupied: int
    tables_total: int
    rooms_occupied: int
    rooms_total: int
    pending_bills: int
    payments_today_count: int
    payments_today_amount: float
    top_menu_items: list[TopMenuItemOut]
    customer_count: int
    loyalty_accounts: int
    loyalty_points_outstanding: float
    website_orders_today: int
    pickup_orders_today: int
    delivery_orders_today: int
    payment_method_breakdown: list[PaymentMethodBreakdownOut]
