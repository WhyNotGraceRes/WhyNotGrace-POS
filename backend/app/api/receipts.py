"""Rendering bills and kitchen tickets for printing.

Two distinct actions, deliberately on different verbs:

  GET  .../receipt   preview. Does NOT count as a print.
  POST .../print     the real thing. Counts, and returns the copy marked
                     DUPLICATE if it is not the first.

Splitting them matters because the DUPLICATE mark is only trustworthy if the
count reflects paper actually produced. If previewing incremented it, a
cashier checking a bill on screen would turn the next genuine print into a
"duplicate"; if printing did not, two originals could be produced with
nothing to show for it.

The duplicate decision is made server-side and baked into the rendered
output, so a client that forgets the rule cannot print an unmarked second
original.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_BILLING, ROLE_KITCHEN
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.kot import KOT
from app.services import audit_service, billing_service
from app.services.receipt import builder
from app.services.receipt.render_escpos import render_escpos
from app.services.receipt.render_html import render_html
from app.services.receipt.render_text import render_text

router = APIRouter(tags=["receipts"])

ReceiptFormat = Literal["html", "text", "escpos"]


def _respond(doc, fmt: ReceiptFormat) -> Response:
    if fmt == "html":
        return Response(content=render_html(doc), media_type="text/html; charset=utf-8")
    if fmt == "text":
        return Response(content=render_text(doc), media_type="text/plain; charset=utf-8")
    # Raw bytes for a print agent to forward straight to the device.
    # application/octet-stream so nothing downstream tries to be helpful and
    # re-encode it — ESC/POS is not text and must not be treated as such.
    return Response(content=render_escpos(doc), media_type="application/octet-stream")


@router.get("/billing/{bill_id}/receipt")
def preview_bill_receipt(
    bill_id: uuid.UUID,
    format: ReceiptFormat = "html",
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_BILLING)),
):
    """Renders the bill without counting it as a print."""
    bill = billing_service.get_bill_or_404(db, business_id, bill_id)
    doc = builder.build_bill_receipt(db, business_id, bill, is_preview=True)
    return _respond(doc, format)


@router.post("/billing/{bill_id}/print-receipt")
def print_bill_receipt(
    bill_id: uuid.UUID,
    format: ReceiptFormat = "html",
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    """Counts a print and returns that copy, marked if it is a duplicate."""
    with transaction(db):
        bill, is_duplicate = billing_service.register_print(db, business_id, bill_id)
        audit_service.record(
            db, action="bill.print", business_id=business_id, user_id=user.id,
            resource_type="bill", resource_id=str(bill.id),
            metadata={"print_count": bill.print_count, "duplicate": is_duplicate, "format": format},
        )
        doc = builder.build_bill_receipt(db, business_id, bill, is_duplicate=is_duplicate)
    return _respond(doc, format)


@router.get("/kot/{kot_id}/ticket")
def kot_ticket(
    kot_id: uuid.UUID,
    format: ReceiptFormat = "html",
    station: str | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_KITCHEN)),
):
    """A kitchen ticket, optionally for one station only.

    Kitchen tickets are not counted or marked as duplicates: reprinting one
    because the paper jammed is routine and carries none of the risk that
    reprinting a bill does.
    """
    kot = db.query(KOT).filter(KOT.id == kot_id, KOT.business_id == business_id).first()
    if kot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOT not found")

    doc = builder.build_kot_ticket(db, business_id, kot, station=station or None)
    return _respond(doc, format)


@router.get("/kot/{kot_id}/stations", response_model=list[str])
def kot_stations(
    kot_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_KITCHEN)),
):
    """Which stations this ticket needs printing to.

    Returned as a list so the caller loops and prints one ticket per station.
    An empty string in the list is the default kitchen — items with no
    station configured.
    """
    kot = db.query(KOT).filter(KOT.id == kot_id, KOT.business_id == business_id).first()
    if kot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOT not found")
    return builder.stations_for_kot(db, business_id, kot)


@router.get("/shifts/{shift_id}/report/print")
def print_shift_report(
    shift_id: uuid.UUID,
    format: ReceiptFormat = "html",
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_BILLING)),
):
    """The Z-report on the counter's own paper.

    Not counted or marked as a duplicate — reprinting a shift report carries
    none of the risk that reprinting a bill does.
    """
    from app.services import shift_service

    shift = shift_service.get_shift_or_404(db, business_id, shift_id)
    report = shift_service.build_report(db, business_id, shift)
    doc = builder.build_shift_report(db, business_id, report)
    return _respond(doc, format)
