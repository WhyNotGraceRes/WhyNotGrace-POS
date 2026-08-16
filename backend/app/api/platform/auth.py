from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.platform_dependencies import get_current_platform_user
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.platform_user import PlatformUser
from app.schemas.platform_auth import (
    GenericMessageResponse,
    PlatformAccessTokenResponse,
    PlatformLoginRequest,
    PlatformLogoutRequest,
    PlatformRefreshRequest,
    PlatformTokenPairResponse,
    PlatformUserOut,
)
from app.services import platform_auth_service

router = APIRouter(prefix="/platform/auth", tags=["platform-auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login", response_model=PlatformTokenPairResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: PlatformLoginRequest, db: Session = Depends(get_db)):
    with transaction(db):
        user = platform_auth_service.authenticate(
            db, email=payload.email, password=payload.password, ip_address=_client_ip(request)
        )
        access_token, refresh_token = platform_auth_service.issue_token_pair(
            db, user, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request)
        )
    return PlatformTokenPairResponse(
        access_token=access_token, refresh_token=refresh_token, user=PlatformUserOut.model_validate(user)
    )


@router.post("/refresh", response_model=PlatformAccessTokenResponse)
@limiter.limit("30/minute")
def refresh(request: Request, payload: PlatformRefreshRequest, db: Session = Depends(get_db)):
    with transaction(db):
        access_token, refresh_token, _user = platform_auth_service.rotate_refresh_token(
            db, payload.refresh_token, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request)
        )
    return PlatformAccessTokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=GenericMessageResponse)
def logout(payload: PlatformLogoutRequest, db: Session = Depends(get_db)):
    with transaction(db):
        platform_auth_service.revoke_refresh_token(db, payload.refresh_token)
    return GenericMessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=PlatformUserOut)
def me(current_user: PlatformUser = Depends(get_current_platform_user)):
    return PlatformUserOut.model_validate(current_user)
