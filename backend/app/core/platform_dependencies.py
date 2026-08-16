"""Auth/RBAC for WhyNotGrace's own staff — the platform-actor counterpart
to app.core.dependencies (business staff) and app.core.permissions (business
roles). Deliberately not merged into either: see app.models.platform_user
for why a platform account is a structurally separate principal.
"""
import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenType, decode_token
from app.database.session import get_db
from app.models.enums import PlatformRole
from app.models.platform_user import PlatformUser

bearer_scheme = HTTPBearer(auto_error=False)

# One role today; kept as an explicit set (mirroring permissions.py's
# ROLE_* groups) so a lower-privilege platform role can be added later by
# widening this set, not by restructuring every route that depends on it.
PLATFORM_ROLE_FULL_ACCESS = {PlatformRole.SUPERADMIN}


def get_current_platform_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> PlatformUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != TokenType.ACCESS.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    # The other half of the wall described in dependencies.get_current_user:
    # this path requires the platform claim rather than merely tolerating a
    # missing business_id, so a business access token (which never carries
    # this claim) cannot be replayed here either.
    if payload.get("actor") != "platform":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a platform account")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    platform_user = db.get(PlatformUser, uuid.UUID(user_id))
    if platform_user is None or not platform_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    request.state.current_platform_user = platform_user
    return platform_user


def require_platform_role(*roles: PlatformRole) -> Callable[..., PlatformUser]:
    allowed = set(roles)

    def _checker(platform_user: PlatformUser = Depends(get_current_platform_user)) -> PlatformUser:
        if platform_user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return platform_user

    return _checker
