import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business, get_current_business_id, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.business import Business
from app.models.enums import LocationType
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.services import audit_service, location_service

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationOut])
def list_locations(
    location_type: LocationType | None = None,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    locations = location_service.list_locations(db, business.id, location_type)
    return [location_service.location_out_dict(business, loc) for loc in locations]


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        location = location_service.create_location(db, business, payload)
        audit_service.record(
            db, action="location.create", business_id=business.id, user_id=user.id,
            resource_type="location", resource_id=str(location.id),
        )
    return location_service.location_out_dict(business, location)


@router.put("/{location_id}", response_model=LocationOut)
def update_location(
    location_id: uuid.UUID,
    payload: LocationUpdate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        location = location_service.update_location(db, business.id, location_id, payload)
        audit_service.record(
            db, action="location.update", business_id=business.id, user_id=user.id,
            resource_type="location", resource_id=str(location_id),
        )
    return location_service.location_out_dict(business, location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        location_service.delete_location(db, business_id, location_id)
        audit_service.record(
            db, action="location.delete", business_id=business_id, user_id=user.id,
            resource_type="location", resource_id=str(location_id),
        )
