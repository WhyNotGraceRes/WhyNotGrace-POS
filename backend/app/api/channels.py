"""Partner-facing order intake.

This is the entire surface a partner credential can reach. It is one POST.
There is no way to list orders, read customers, query the menu, or touch
another tenant — a channel key is an order-submission capability, not an API
account, and keeping the surface this small is most of why a leaked key is
survivable.

Rate limited per channel key rather than per IP: a partner site is a server,
so all of its traffic legitimately arrives from one address, and an IP key
would either be uselessly loose or throttle a busy site's real customers.
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.partner_auth import get_partner_channel
from app.core.rate_limit import limiter, partner_channel_key
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.partner import PartnerChannel
from app.schemas.partner import PartnerOrderAck, PartnerOrderCreate
from app.services import audit_service, customer_service, partner_service

router = APIRouter(prefix="/channels", tags=["partner-channel-orders"])


@router.post("/orders", response_model=PartnerOrderAck, status_code=status.HTTP_201_CREATED)
@limiter.limit("120/minute", key_func=partner_channel_key)
def submit_order(
    request: Request,
    payload: PartnerOrderCreate,
    channel: PartnerChannel = Depends(get_partner_channel),
    db: Session = Depends(get_db),
):
    """Accepts an order from a provisioned partner site.

    Note what the handler never does: read a business id from the payload,
    or read a price from it. The tenant comes from the authenticated
    channel; the money comes from pricing_service.
    """
    with transaction(db):
        customer_id = None
        if payload.customer is not None:
            customer = customer_service.get_or_create_by_mobile(db, channel.business_id, payload.customer)
            customer_id = customer.id

        order, was_duplicate = partner_service.submit_order(db, channel, payload)

        if customer_id is not None and order.customer_id is None:
            order.customer_id = customer_id
            db.flush()

        if not was_duplicate:
            # user_id is null by construction — no staff member performed
            # this. The channel is recorded in metadata so an order can
            # always be traced back to which site submitted it.
            audit_service.record(
                db, action="partner_channel.order_submitted", business_id=channel.business_id,
                user_id=None, resource_type="order", resource_id=str(order.id),
                metadata={"channel_key_id": channel.key_id, "channel_name": channel.name},
            )

    return PartnerOrderAck(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        subtotal=float(order.subtotal),
        duplicate=was_duplicate,
    )
