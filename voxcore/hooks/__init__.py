"""Pluggable hooks for side-effects VoxCore itself does not implement.

VoxCore ships no-op defaults so downstream projects can wire billing, device
binding, or SIEM export without forking the core.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BillingHook:
    """Override in downstream products that meter usage.

    Default behavior: record nothing. Return ``True`` to allow the operation.
    """

    async def can_consume(self, user_id: int, service: str, amount: float) -> bool:  # noqa: ARG002
        return True

    async def record_usage(
        self, user_id: int, service: str, amount: float, extra: dict[str, Any] | None = None
    ) -> None:
        return None


class AuditHook:
    """Override to forward audit events to SIEM / data warehouse."""

    async def emit(
        self,
        *,
        event_type: str,
        user_id: int | None,
        client_ip: str | None,
        success: bool,
        detail: dict[str, Any] | None = None,
    ) -> None:
        logger.info(
            "audit",
            extra={
                "event_type": event_type,
                "user_id": user_id,
                "client_ip": client_ip,
                "success": success,
                "detail": detail or {},
            },
        )


__all__ = ["AuditHook", "BillingHook"]
