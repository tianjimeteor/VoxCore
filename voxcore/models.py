"""ORM models for VoxCore.

Kept minimal: only what's needed for auth + audit + rate limiting. Business
concepts (billing, device binding, redemption) belong in downstream projects.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SecurityLog(Base):
    """Audit trail for sensitive operations (login, registration, etc.)."""

    __tablename__ = "security_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )


class RateLimitRecord(Base):
    """Fixed-window rate-limit bookkeeping (per key + action)."""

    __tablename__ = "rate_limit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    first_attempt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_attempt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
