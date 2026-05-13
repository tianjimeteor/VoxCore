"""Per-connection session state passed to user handlers as `ctx`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket

    from ..adapters.asr.base import ASRAdapter
    from ..adapters.llm.base import LLMAdapter
    from ..adapters.vision.base import VisionAdapter


@dataclass
class SessionContext:
    """Handed to `@on_transcript` handlers. Lightweight by design."""

    session_id: str
    user_id: int | None = None
    websocket: "WebSocket | None" = None
    asr: "ASRAdapter | None" = None
    llm: "LLMAdapter | None" = None
    vision: "VisionAdapter | None" = None
    metadata: dict[str, Any] = field(default_factory=dict)

    async def send(self, chunk: str) -> None:
        """Send a text chunk back to the client over WebSocket."""
        if self.websocket is None:
            return
        await self.websocket.send_json({"type": "chunk", "text": chunk})

    async def send_event(self, event: str, **payload: Any) -> None:
        if self.websocket is None:
            return
        await self.websocket.send_json({"type": event, **payload})
