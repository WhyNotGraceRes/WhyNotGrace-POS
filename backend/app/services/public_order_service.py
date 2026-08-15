"""Shared checkout logic for the public Pickup and Delivery flows:
website -> menu -> cart -> customer details -> Razorpay -> verified
payment -> order released to POS/KOT. Both app/api/pickup.py and
app/api/delivery.py call this so the flow stays identical apart from the
OrderSource and the delivery address requirement.
"""
from sqlalchemy.orm import Session

from app.core.dependencies import require_feature_for_business
from app.models.enums import FeatureModule, OrderSource
from app.models.order import Order
from app.schemas.billing import GenerateBillRequest
from app.schemas.customer import CustomerCreate
from app.schemas.payment import RazorpayOrderCreateRequest, RazorpayVerifyRequest
from app.services import billing_service, customer_service, order_service, payment_service, qr_service


def checkout(
    db: Session, *, business_slug: str, source: OrderSource, customer_info, items, notes: str | None,
    delivery_address: str | None = None, delivery_instructions: str | None = None,
):
    business = qr_service.get_business_by_slug_or_404(db, business_slug)
    module = FeatureModule.PICKUP if source == OrderSource.PICKUP else FeatureModule.DELIVERY
    require_feature_for_business(db, business.id, module)
    require_feature_for_business(db, business.id, FeatureModule.ONLINE_PAYMENT)

    customer = customer_service.get_or_create_by_mobile(
        db, business.id, CustomerCreate(first_name=customer_info.first_name, mobile=customer_info.mobile, email=customer_info.email)
    )

    order = order_service.create_order(
        db,
        business_id=business.id,
        location_id=None,
        source=source,
        pricing_context=None,
        items_payload=items,
        customer_id=customer.id,
        notes=notes,
        delivery_address=delivery_address,
        delivery_instructions=delivery_instructions,
        hold_kot=True,
    )

    bill = billing_service.generate_or_refresh_bill(db, business.id, GenerateBillRequest(session_id=order.session_id))
    payment, provider_order_id, razorpay_key_id = payment_service.create_razorpay_order(
        db, business.id, RazorpayOrderCreateRequest(bill_id=bill.id)
    )

    return order, payment, provider_order_id, razorpay_key_id


def verify_checkout(db: Session, *, business_slug: str, payload: RazorpayVerifyRequest) -> Order:
    from app.models.billing import Bill

    business = qr_service.get_business_by_slug_or_404(db, business_slug)
    payment = payment_service.verify_razorpay_payment(db, business.id, payload)
    bill = db.get(Bill, payment.bill_id)
    order = db.query(Order).filter(Order.business_id == business.id, Order.session_id == bill.session_id).first()
    return order
