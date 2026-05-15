"""Real-time WebSocket gateway.

Protocol (JSON over WebSocket):

    Client → Server:
        {"type": "audio", "data": "<base64 PCM16LE 16k mono>"}
        {"type": "text", "text": "user text, skips ASR"}

    Server → Client:
        {"type": "transcript", "text": "...", "final": true}
        {"type": "chunk", "text": "..."}           # LLM streaming chunk
        {"type": "error", "detail": "..."}

Auth: connect with ``?token=<JWT>`` query param.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from ..auth import decode_access_token
from ..core.session import SessionContext

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gateway"])


@router.websocket("/ws")
async def gateway(websocket: WebSocket, token: str = Query(default="")) -> None:
    # ---- auth --------------------------------------------------------------
    payload = decode_access_token(token) if token else None
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # ---- context -----------------------------------------------------------
    facade = websocket.app.state.voxcore  # set by VoxCore.__init__
    settings = facade.settings

    ctx = SessionContext(
        session_id=uuid.uuid4().hex,
        user_id=user_id,
        websocket=websocket,
        asr=facade.asr,
        llm=facade.llm,
        vision=facade.vision,
    )

    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=64)

    async def audio_source() -> AsyncIterator[bytes]:
        while True:
            item = await audio_queue.get()
            if item is None:
                return
            yield item

    async def asr_pump() -> None:
        if facade.asr is None:
            return
        async for transcript in facade.asr.stream(audio_source()):
            await websocket.send_json(
                {"type": "transcript", "text": transcript.text, "final": transcript.is_final}
            )
            if transcript.is_final:
                await facade.dispatch_transcript(transcript.text, ctx)

    asr_task = asyncio.create_task(asr_pump())

    try:
        while True:
            msg = await asyncio.wait_for(
                websocket.receive_json(), timeout=settings.ws_heartbeat_seconds
            )

            mtype = msg.get("type")
            if mtype == "audio":
                data = base64.b64decode(msg.get("data", ""))
                if len(data) > settings.ws_max_message_bytes:
                    await websocket.send_json(
                        {"type": "error", "detail": "audio chunk too large"}
                    )
                    continue
                await audio_queue.put(data)

            elif mtype == "text":
                text = str(msg.get("text", "")).strip()
                if text:
                    await websocket.send_json(
                        {"type": "transcript", "text": text, "final": True}
                    )
                    await facade.dispatch_transcript(text, ctx)

            elif mtype == "eof":
                await audio_queue.put(None)

            else:
                await websocket.send_json(
                    {"type": "error", "detail": f"unknown message type: {mtype}"}
                )

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception:
        logger.exception("gateway loop failed")
    finally:
        await audio_queue.put(None)
        asr_task.cancel()
        try:
            await asr_task
        except (asyncio.CancelledError, Exception):  # noqa: S110
            pass  # ASR task already torn down; nothing to do here
