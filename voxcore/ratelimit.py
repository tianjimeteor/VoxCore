"""Fixed-window rate limiter backed by the `rate_limit_records` table.

Why not Redis? The open-source default must work with zero ops. Swap in Redis
for production by subclassing `RateLimiter` and wiring via dependency override.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal
from .models import RateLimitRecord

settings = get_settings()


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(retry_after)},
        )


def _client_ip(request: Request) -> str:
    # Honor X-Forwarded-For only when explicitly trusted upstream; default to peer.
    # Operators should terminate the trusted proxy and set `X-Real-IP`.
    return request.client.host if request.client else "unknown"


def check_rate_limit(
    request: Request,
    action: str,
    *,
    max_attempts: int | None = None,
    window_seconds: int | None = None,
    lockout_seconds: int | None = None,
) -> None:
    """Raise RateLimitExceeded if the IP has exceeded the quota for `action`."""
    max_attempts = max_attempts or settings.login_rate_limit_max_attempts
    window_seconds = window_seconds or settings.login_rate_limit_window_seconds
    lockout_seconds = lockout_seconds or settings.login_lockout_duration_seconds

    key = f"{_client_ip(request)}:{action}"
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)

    db: Session = SessionLocal()
    try:
        record = (
            db.query(RateLimitRecord)
            .filter(RateLimitRecord.key == key, RateLimitRecord.action == action)
            .one_or_none()
        )

        if record is None:
            db.add(
                RateLimitRecord(
                    key=key, action=action, attempts=1, first_attempt=now, last_attempt=now
                )
            )
            db.commit()
            return

        # Lockout still active?
        if (
            record.attempts >= max_attempts
            and (now - record.last_attempt).total_seconds() < lockout_seconds
        ):
            raise RateLimitExceeded(
                retry_after=int(
                    lockout_seconds - (now - record.last_attempt).total_seconds()
                )
            )

        # Window rolled over → reset.
        if record.first_attempt < window_start:
            record.attempts = 1
            record.first_attempt = now
        else:
            record.attempts += 1
        record.last_attempt = now
        db.commit()

        if record.attempts > max_attempts:
            raise RateLimitExceeded(retry_after=lockout_seconds)
    finally:
        db.close()
