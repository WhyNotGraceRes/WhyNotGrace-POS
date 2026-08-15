from fastapi import APIRouter, Depends, Request, status
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
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenPairResponse,
    UserOut,
    VerifyEmailRequest,
)
from app.services import auth_service
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    with transaction(db):
        owner = auth_service.register_business(db, payload)
    return RegisterResponse(business_id=owner.business_id, user_id=owner.id, email=owner.email)


@router.post("/verify-email", response_model=GenericMessageResponse)
@limiter.limit("10/minute")
def verify_email(request: Request, payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    with transaction(db):
        auth_service.verify_email(db, payload.email, payload.code)
    return GenericMessageResponse(message="Email verified successfully. You can now log in.")


@router.post("/resend-verification", response_model=GenericMessageResponse)
@limiter.limit("5/minute")
def resend_verification(request: Request, payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    with transaction(db):
        auth_service.resend_verification(db, payload.email)
    return GenericMessageResponse(
        message="If an account with that email exists and is not yet verified, a new code has been sent."
    )


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
