"""Shared FastAPI dependencies: DB session, authenticated user, tenant
context, RBAC enforcement, and feature-flag enforcement.

CRITICAL SECURITY RULE: business_id is NEVER read from a path/query/body
parameter for authenticated staff endpoints. It is always derived from the
JWT via get_current_user -> current_user.business_id. Every repository
call must filter by this value.
"""
import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenType, decode_token
from app.database.session import get_db
from app.models.business import Business
from app.models.enums import FeatureModule, ALWAYS_ON_FEATURES, UserRole
from app.models.feature_flag import FeatureFlag
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != TokenType.ACCESS.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    request.state.current_user = user
    return user


def get_current_business(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Business:
    business = db.get(Business, current_user.business_id)
    if business is None or not business.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business not found or inactive")
    return business


def get_current_business_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    return current_user.business_id


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    allowed = set(allowed_roles)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _checker


def require_feature(module: FeatureModule) -> Callable[..., None]:
    """Enforce that a business has a module enabled before allowing the
    request through. This is the server-side gate that a frontend cannot
    bypass by calling the API directly.
    """

    def _checker(
        business_id: uuid.UUID = Depends(get_current_business_id),
        db: Session = Depends(get_db),
    ) -> None:
        if module in ALWAYS_ON_FEATURES:
            return
        flag = (
            db.query(FeatureFlag)
            .filter(FeatureFlag.business_id == business_id, FeatureFlag.module == module)
            .first()
        )
        if flag is None or not flag.enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The '{module.value}' module is not enabled for this business",
            )

    return _checker


def require_feature_for_business(db: Session, business_id: uuid.UUID, module: FeatureModule) -> None:
    """Non-dependency variant for use inside public (unauthenticated) QR /
    website / pickup / delivery endpoints, where business_id comes from a
    slug/QR code rather than a JWT, but must still be validated against a
    real business row before any flag check.
    """
    if module in ALWAYS_ON_FEATURES:
        return
    flag = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.business_id == business_id, FeatureFlag.module == module)
        .first()
    )
    if flag is None or not flag.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The '{module.value}' module is not enabled for this business",
        )
