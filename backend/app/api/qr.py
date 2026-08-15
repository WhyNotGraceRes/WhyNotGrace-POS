"""Public, unauthenticated QR ordering endpoints. No customer account is
required. Access is scoped entirely by a per-location QR session token —
never by a client-supplied business_id.

Each route obtains `db` the normal FastAPI way (Depends(get_qr_db), bound to
the separate QR connection pool — see app/database/session.py), then
dispatches its actual DB-query-containing work via
anyio.to_thread.run_sync(..., limiter=qr_thread_limiter) instead of letting
it run on FastAPI's default per-route threadpool dispatch. This matters
because a real load test proved DB-pool isolation alone does not protect
the staff dashboard: Starlette/FastAPI dispatch every sync route through
ONE shared, process-wide anyio default thread limiter (capacity 40)
regardless of which DB engine it queries, so QR requests blocked waiting on
the (deliberately small) QR pool were still occupying threads the staff
dashboard needed — 52s median staff /orders latency with zero staff DB
errors, purely from thread starvation. Routing the query-containing work
through a QR-only CapacityLimiter (see app/core/request_limits.py) bounds
how many threads QR traffic can ever occupy, guaranteeing the rest for
every other route. get_qr_db() itself stays on the default limiter — it
only constructs a Session object (no I/O, sub-millisecond), so it can't
meaningfully compete with staff for those threads even under heavy QR load.
"""
import uuid

import anyio
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_feature_for_business
from app.core.rate_limit import limiter
from app.core.request_limits import qr_thread_limiter
from app.database.session import get_qr_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule, OrderSource
from app.schemas.order import OrderOut
from app.schemas.qr import QRMenuResponse, QROrderCreateRequest, QRScanResponse
from app.services import order_service, qr_service

router = APIRouter(prefix="/qr", tags=["qr-ordering"])


def _scan_qr_sync(db: Session, business_slug: str, location_id: uuid.UUID, code: str) -> QRScanResponse:
    with transaction(db):
        session, business, location = qr_service.start_session(
            db, business_slug=business_slug, location_id=location_id, code=code
        )
    return QRScanResponse(
        session_token=session.session_token,
        business_id=business.id,
        business_name=business.name,
        location_id=location.id,
        location_type=location.location_type,
        location_name=location.name,
        expires_at=session.expires_at.isoformat(),
    )


@router.get("/scan/{business_slug}/{location_id}", response_model=QRScanResponse)
@limiter.limit("30/minute")
async def scan_qr(
    request: Request,
    business_slug: str,
    location_id: uuid.UUID,
    c: str,
    db: Session = Depends(get_qr_db),
):
    return await anyio.to_thread.run_sync(
        _scan_qr_sync, db, business_slug, location_id, c, limiter=qr_thread_limiter
    )


def _get_menu_sync(db: Session, session_token: str, lang: str) -> QRMenuResponse:
    session = qr_service.get_active_session_or_404(db, session_token)
    require_feature_for_business(db, session.business_id, FeatureModule.QR_ORDERING)
    from app.models.business import Business
    from app.models.location import Location

    business = db.get(Business, session.business_id)
    location = db.get(Location, session.location_id)
    if business is None or location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return qr_service.build_menu_response(db, business, location, language=lang)


@router.get("/menu", response_model=QRMenuResponse)
async def get_menu(
    lang: str = "en",
    session_token: str = Header(..., alias="X-QR-Session"),
    db: Session = Depends(get_qr_db),
):
    return await anyio.to_thread.run_sync(_get_menu_sync, db, session_token, lang, limiter=qr_thread_limiter)


def _place_qr_order_sync(db: Session, session_token: str, payload: QROrderCreateRequest) -> OrderOut:
    session = qr_service.get_active_session_or_404(db, session_token)
    require_feature_for_business(db, session.business_id, FeatureModule.QR_ORDERING)
    with transaction(db):
        order = order_service.create_order(
            db,
            business_id=session.business_id,
            location_id=session.location_id,
            source=OrderSource.QR,
            pricing_context=None,
            items_payload=payload.items,
            notes=payload.notes,
        )
    return OrderOut.model_validate(order)


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def place_qr_order(
    request: Request,
    payload: QROrderCreateRequest,
    session_token: str = Header(..., alias="X-QR-Session"),
    db: Session = Depends(get_qr_db),
):
    return await anyio.to_thread.run_sync(
        _place_qr_order_sync, db, session_token, payload, limiter=qr_thread_limiter
    )


def _get_qr_order_status_sync(db: Session, session_token: str, order_id: uuid.UUID) -> OrderOut:
    session = qr_service.get_active_session_or_404(db, session_token)
    order = order_service.get_order_or_404(db, session.business_id, order_id)
    if order.location_id != session.location_id:
        # Do not leak orders from other locations/tables via this session.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderOut.model_validate(order)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_qr_order_status(
    order_id: uuid.UUID,
    session_token: str = Header(..., alias="X-QR-Session"),
    db: Session = Depends(get_qr_db),
):
    return await anyio.to_thread.run_sync(
        _get_qr_order_status_sync, db, session_token, order_id, limiter=qr_thread_limiter
    )
