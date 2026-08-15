"""Thin convenience wrapper over the generic Location model, scoped to
LocationType.ROOM. Uses the same service/storage as /locations.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business, require_feature, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.business import Business
from app.models.enums import FeatureModule, LocationType
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.services import audit_service, location_service

router = APIRouter(prefix="/rooms", tags=["rooms"], dependencies=[Depends(require_feature(FeatureModule.HOTEL_ROOMS))])


@router.get("", response_model=list[LocationOut])
def list_rooms(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    rooms = location_service.list_locations(db, business.id, LocationType.ROOM)
    return [location_service.location_out_dict(business, r) for r in rooms]


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: LocationCreate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    payload.location_type = LocationType.ROOM
    with transaction(db):
        room = location_service.create_location(db, business, payload)
        audit_service.record(
            db, action="room.create", business_id=business.id, user_id=user.id,
            resource_type="location", resource_id=str(room.id),
        )
    return location_service.location_out_dict(business, room)


@router.put("/{room_id}", response_model=LocationOut)
def update_room(
    room_id: uuid.UUID,
    payload: LocationUpdate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        room = location_service.update_location(db, business.id, room_id, payload)
        audit_service.record(
            db, action="room.update", business_id=business.id, user_id=user.id,
            resource_type="location", resource_id=str(room_id),
        )
    return location_service.location_out_dict(business, room)
