import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_feature, require_feature_for_business, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule
from app.models.review import Review
from app.schemas.review import ReviewCreateRequest, ReviewOut
from app.services import audit_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewOut], dependencies=[Depends(require_feature(FeatureModule.REVIEWS))])
def list_reviews(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    reviews = db.query(Review).filter(Review.business_id == business_id).order_by(Review.created_at.desc()).all()
    return [ReviewOut.model_validate(r) for r in reviews]


@router.post("/public/{business_slug}", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def submit_review(
    business_slug: str,
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
):
    """Public endpoint — a customer submits a review after a completed
    order, no account required. Still gated by the REVIEWS feature flag.
    """
    from app.models.business import Business

    business = db.query(Business).filter(Business.slug == business_slug, Business.is_active.is_(True)).first()
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    require_feature_for_business(db, business.id, FeatureModule.REVIEWS)

    with transaction(db):
        review = Review(business_id=business.id, **payload.model_dump())
        db.add(review)
        db.flush()
    return ReviewOut.model_validate(review)
