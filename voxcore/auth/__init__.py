"""JWT + password utilities and FastAPI auth dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import User

settings = get_settings()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=True)


# ----- password --------------------------------------------------------------

def hash_password(plain: str) -> str:
    if len(plain) < settings.min_password_length:
        raise ValueError(
            f"password must be at least {settings.min_password_length} characters"
        )
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


# ----- JWT -------------------------------------------------------------------

def create_access_token(
    sub: str, *, extra: dict[str, Any] | None = None, ttl: timedelta | None = None
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": now,
        "exp": now + (ttl or timedelta(days=settings.jwt_expire_days)),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None


# ----- FastAPI dependencies --------------------------------------------------

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise _UNAUTHORIZED

    sub = payload.get("sub")
    if not sub:
        raise _UNAUTHORIZED
    try:
        user_id = int(sub)
    except (TypeError, ValueError) as err:
        raise _UNAUTHORIZED from err

    user = db.get(User, user_id)
    if user is None:
        raise _UNAUTHORIZED
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User disabled"
        )
    return user
