"""Thin convenience wrapper over the generic Location model, scoped to
LocationType.TABLE. Uses the same service/storage as /locations.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.business import Business
from app.models.enums import LocationType
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.services import audit_service, location_service

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("", response_model=list[LocationOut])
def list_tables(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    tables = location_service.list_locations(db, business.id, LocationType.TABLE)
    return [location_service.location_out_dict(business, t) for t in tables]


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_table(
    payload: LocationCreate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    payload.location_type = LocationType.TABLE
    with transaction(db):
        table = location_service.create_location(db, business, payload)
        audit_service.record(
            db, action="table.create", business_id=business.id, user_id=user.id,
            resource_type="location", resource_id=str(table.id),
        )
    return location_service.location_out_dict(business, table)


@router.put("/{table_id}", response_model=LocationOut)
def update_table(
    table_id: uuid.UUID,
    payload: LocationUpdate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        table = location_service.update_location(db, business.id, table_id, payload)
        audit_service.record(
            db, action="table.update", business_id=business.id, user_id=user.id,
            resource_type="location", resource_id=str(table_id),
        )
    return location_service.location_out_dict(business, table)
