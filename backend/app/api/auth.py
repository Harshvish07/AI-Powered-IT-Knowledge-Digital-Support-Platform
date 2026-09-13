from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _set_refresh_cookie(response: Response, token: str, expires_at: datetime) -> None:
    max_age = int((expires_at - datetime.now(UTC)).total_seconds())
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.refresh_cookie_name, path="/api/auth")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user = auth_service.register_user(
            db, email=payload.email, password=payload.password, full_name=payload.full_name
        )
    except auth_service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        ) from exc

    access_token, expires_in, refresh_token, refresh_expires_at = auth_service.issue_token_pair(
        db, user
    )
    _set_refresh_cookie(response, refresh_token, refresh_expires_at)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        ) from exc
    except auth_service.AccountDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        ) from exc

    access_token, expires_in, refresh_token, refresh_expires_at = auth_service.issue_token_pair(
        db, user
    )
    _set_refresh_cookie(response, refresh_token, refresh_expires_at)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )

    try:
        _, access_token, expires_in, new_refresh_token, new_expires_at = (
            auth_service.rotate_refresh_token(db, raw_refresh_token)
        )
    except auth_service.InvalidRefreshTokenError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        ) from exc

    _set_refresh_cookie(response, new_refresh_token, new_expires_at)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh_token:
        auth_service.revoke_refresh_token(db, raw_refresh_token)
    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}
