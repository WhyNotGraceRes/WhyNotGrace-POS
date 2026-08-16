"""Business staff login. There is no self-registration here — a business
only exists because a platform admin provisioned it (see
app.api.platform.businesses), and the owner account that creates is active
and pre-verified from the start. Email verification accordingly has no
remaining caller and was removed along with /register; see
app.services.auth_service if that history is needed again.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    GenericMessageResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPairResponse,
    UserOut,
)
from app.services import auth_service
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenPairResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    with transaction(db):
        user = auth_service.authenticate(
            db, identifier=payload.identifier, password=payload.password, ip_address=_client_ip(request)
        )
        access_token, refresh_token = auth_service.issue_token_pair(
            db, user, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request)
        )
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=AccessTokenResponse)
@limiter.limit("30/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)):
    with transaction(db):
        access_token, refresh_token, _user = auth_service.rotate_refresh_token(
            db, payload.refresh_token, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request)
        )
    return AccessTokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=GenericMessageResponse)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    with transaction(db):
        auth_service.revoke_refresh_token(db, payload.refresh_token)
    return GenericMessageResponse(message="Logged out successfully.")


@router.post("/forgot-password", response_model=GenericMessageResponse)
@limiter.limit("5/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    with transaction(db):
        auth_service.request_password_reset(db, payload.email)
    return GenericMessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=GenericMessageResponse)
@limiter.limit("10/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    with transaction(db):
        auth_service.reset_password(db, payload.token, payload.new_password)
    return GenericMessageResponse(message="Password reset successfully. Please log in with your new password.")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
