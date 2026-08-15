import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import generate_url_safe_token
from app.models.business import Business
from app.models.enums import LocationType
from app.models.location import Location, QRCode

settings = get_settings()


def _qr_url(business: Business, location: Location, qr: QRCode) -> str:
    kind = "table" if location.location_type == LocationType.TABLE else "room" if location.location_type == LocationType.ROOM else "location"
    return f"{settings.frontend_base_url}/qr/menu/{business.slug}/{kind}/{location.id}?c={qr.code}"


def list_locations(db: Session, business_id: uuid.UUID, location_type: LocationType | None = None) -> list[Location]:
    query = db.query(Location).filter(Location.business_id == business_id)
    if location_type:
        query = query.filter(Location.location_type == location_type)
    return query.order_by(Location.name).all()


def get_location_or_404(db: Session, business_id: uuid.UUID, location_id: uuid.UUID) -> Location:
    location = db.query(Location).filter(Location.id == location_id, Location.business_id == business_id).first()
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


def create_location(db: Session, business: Business, payload) -> Location:
    location = Location(business_id=business.id, **payload.model_dump())
    db.add(location)
    db.flush()

    qr = QRCode(business_id=business.id, location_id=location.id, code=generate_url_safe_token(16))
    db.add(qr)
    db.flush()
    location.qr_code = qr
    return location


def update_location(db: Session, business_id: uuid.UUID, location_id: uuid.UUID, payload) -> Location:
    location = get_location_or_404(db, business_id, location_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    db.flush()
    return location


def delete_location(db: Session, business_id: uuid.UUID, location_id: uuid.UUID) -> None:
    location = get_location_or_404(db, business_id, location_id)
    db.delete(location)
    db.flush()


def location_out_dict(business: Business, location: Location) -> dict:
    from app.schemas.location import LocationOut

    qr_url = _qr_url(business, location, location.qr_code) if location.qr_code else None
    return LocationOut(
        id=location.id,
        location_type=location.location_type,
        name=location.name,
        capacity=location.capacity,
        floor=location.floor,
        room_type=location.room_type,
        status=location.status,
        is_active=location.is_active,
        qr_url=qr_url,
    )
