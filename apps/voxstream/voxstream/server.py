"""VoxStream caption server.

A tiny FastAPI app that:

* Captures system / mic audio (see ``capture.py``).
* Streams it through a VoxCore ASR adapter.
* Broadcasts each transcript over a WebSocket to every connected OBS Browser
  Source (and translates if requested).

The OBS user does not run Python. They double-click the bundled exe, then add
``http://localhost:7860/overlay?theme=streaming`` as a Browser Source.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from voxcore.adapters.asr import get_asr_adapter
from voxcore.adapters.llm import get_llm_adapter

from . import __version__
from .capture import AudioCapture, CaptureUnavailable

logger = logging.getLogger("voxstream.server")

# overlay/ ships next to the package; PyInstaller adds it via --add-data.
_HERE = Path(__file__).resolve().parent
_OVERLAY_DIR = (_HERE.parent / "overlay").resolve()


class CaptionBroadcaster:
    """Fan-out a transcript stream to every connected WebSocket client."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info("overlay connected (%d total)", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        logger.info("overlay disconnected (%d total)", len(self._clients))

    async def broadcast(self, payload: dict) -> None:
        msg = json.dumps(payload, ensure_ascii=False)
        async with self._lock:
            stale: list[WebSocket] = []
            for ws in self._clients:
                try:
                    await ws.send_text(msg)
                except Exception:  # noqa: BLE001
                    stale.append(ws)
            for ws in stale:
                self._clients.discard(ws)


def create_app(
    *,
    asr: str = "echo",
    translate_to: str | None = None,
    llm_for_translate: str = "echo",
) -> FastAPI:
    """Create the VoxStream FastAPI app.

    Parameters
    ----------
    asr : adapter name registered with ``voxcore.adapters.asr``.
    translate_to : ISO code (e.g. ``"zh"``); when set, finalized transcripts
        are passed through the LLM adapter for translation before broadcast.
    """
    app = FastAPI(title="VoxStream", version=__version__)
    bus = CaptionBroadcaster()
    app.state.bus = bus
    app.state.asr_name = asr
    app.state.translate_to = translate_to

    asr_adapter = get_asr_adapter(asr)
    llm_adapter = get_llm_adapter(llm_for_translate) if translate_to else None
    capture: AudioCapture | None = None
    pump_task: asyncio.Task | None = None

    @app.on_event("startup")
    async def _startup() -> None:
        nonlocal capture, pump_task
        try:
            capture = AudioCapture()
        except CaptureUnavailable as err:
            logger.warning("audio capture unavailable: %s", err)
            return
        pump_task = asyncio.create_task(_pump(capture, asr_adapter, bus, llm_adapter, translate_to))

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        if pump_task:
            pump_task.cancel()
        if capture:
            capture.close()

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "version": __version__,
                "asr": asr,
                "translate_to": translate_to,
                "clients": len(bus._clients),
            }
        )

    @app.websocket("/ws/caption")
    async def caption_ws(ws: WebSocket) -> None:
        await bus.connect(ws)
        try:
            while True:
                # We do not expect inbound messages, but keep the socket warm.
                await ws.receive_text()
        except WebSocketDisconnect:
            await bus.disconnect(ws)
        except Exception:  # noqa: BLE001
            await bus.disconnect(ws)

    if _OVERLAY_DIR.is_dir():
        app.mount("/overlay/static", StaticFiles(directory=str(_OVERLAY_DIR)), name="overlay-static")

        @app.get("/overlay")
        async def overlay_index() -> FileResponse:
            return FileResponse(str(_OVERLAY_DIR / "index.html"))

        @app.get("/overlay/{path:path}")
        async def overlay_asset(path: str) -> FileResponse:
            target = (_OVERLAY_DIR / path).resolve()
            # Path-traversal guard.
            if not str(target).startswith(str(_OVERLAY_DIR)):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            if not target.is_file():
                return JSONResponse({"error": "not found"}, status_code=404)
            return FileResponse(str(target))

    return app


async def _pump(
    capture: AudioCapture,
    asr_adapter,
    bus: CaptionBroadcaster,
    llm_adapter,
    translate_to: str | None,
) -> None:
    """Drive audio → ASR → broadcast loop."""
    try:
        async for transcript in asr_adapter.stream(_audio_iter(capture)):
            payload = {
                "text": transcript.text,
                "final": transcript.is_final,
                "confidence": transcript.confidence,
                "lang": "auto",
            }
            await bus.broadcast(payload)

            if transcript.is_final and translate_to and llm_adapter:
                translated = await _translate(llm_adapter, transcript.text, translate_to)
                await bus.broadcast(
                    {"text": translated, "final": True, "lang": translate_to, "translated": True}
                )
    except asyncio.CancelledError:
        return
    except Exception:  # noqa: BLE001
        logger.exception("pump terminated")


async def _audio_iter(capture: AudioCapture) -> AsyncIterator[bytes]:
    while True:
        chunk = await capture.read()
        if chunk is None:
            await asyncio.sleep(0.05)
            continue
        yield chunk


async def _translate(llm, text: str, target_lang: str) -> str:
    parts: list[str] = []
    prompt = (
        f"Translate the following to {target_lang}. "
        f"Output only the translation, no explanation.\n\n{text}"
    )
    async for chunk in llm.complete(prompt):
        parts.append(chunk)
    return "".join(parts).strip() or text


def main() -> None:
    """Entry point for ``python -m voxstream`` (mostly for tests)."""
    import uvicorn

    asr = os.environ.get("VOXSTREAM_ASR", "echo")
    port = int(os.environ.get("VOXSTREAM_PORT", "7860"))
    uvicorn.run(create_app(asr=asr), host="127.0.0.1", port=port)


if __name__ == "__main__":  # pragma: no cover
    main()
