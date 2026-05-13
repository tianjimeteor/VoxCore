"""Authentication endpoints — register / login / me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..database import get_db
from ..models import SecurityLog, User
from ..ratelimit import check_rate_limit
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


def _log(
    db: Session,
    *,
    event: str,
    user_id: int | None,
    username: str | None,
    client_ip: str | None,
    success: bool,
    detail: str | None = None,
) -> None:
    db.add(
        SecurityLog(
            event_type=event,
            user_id=user_id,
            username=username,
            client_ip=client_ip,
            success=success,
            detail=detail,
        )
    )
    db.commit()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    check_rate_limit(request, "register", max_attempts=5, window_seconds=300)

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "username taken")

    try:
        hashed = hash_password(payload.password)
    except ValueError as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(err)) from err

    user = User(username=payload.username, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)

    _log(
        db,
        event="register",
        user_id=user.id,
        username=user.username,
        client_ip=request.client.host if request.client else None,
        success=True,
    )

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    check_rate_limit(request, "login")
    ip = request.client.host if request.client else None

    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        _log(
            db,
            event="login",
            user_id=user.id if user else None,
            username=payload.username,
            client_ip=ip,
            success=False,
            detail="invalid credentials",
        )
        # Same error for unknown-user and wrong-password to prevent enumeration.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "user disabled")

    _log(
        db,
        event="login",
        user_id=user.id,
        username=user.username,
        client_ip=ip,
        success=True,
    )
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(id=user.id, username=user.username, is_active=user.is_active)
