"""The `VoxCore` facade — the object users interact with at the top of their app.

Responsibilities:

* Resolve adapter names (`asr="xunfei"`) to concrete implementations.
* Collect user-registered handlers (`@app.on_transcript`).
* Expose `.asgi()` so the same object can be deployed behind uvicorn or used
  in tests with `TestClient`.
* `.run()` as a convenience for the 20-line demo.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..adapters.asr.base import ASRAdapter
from ..adapters.llm.base import LLMAdapter
from ..adapters.vision.base import VisionAdapter
from ..config import get_settings
from ..hooks import AuditHook, BillingHook
from .session import SessionContext

logger = logging.getLogger(__name__)

TranscriptHandler = Callable[[str, SessionContext], Awaitable[None]]


class VoxCore:
    """The opinionated entry point. Wraps a FastAPI app with sensible defaults."""

    def __init__(
        self,
        *,
        asr: str | ASRAdapter | None = None,
        llm: str | LLMAdapter | None = None,
        vision: str | VisionAdapter | None = None,
        billing_hook: BillingHook | None = None,
        audit_hook: AuditHook | None = None,
        title: str = "VoxCore",
        version: str = "0.1.0",
    ) -> None:
        self.settings = get_settings()
        self.asr: ASRAdapter | None = _resolve_asr(asr)
        self.llm: LLMAdapter | None = _resolve_llm(llm)
        self.vision: VisionAdapter | None = _resolve_vision(vision)
        self.billing_hook = billing_hook or BillingHook()
        self.audit_hook = audit_hook or AuditHook()

        self._transcript_handlers: list[TranscriptHandler] = []
        self.app = self._build_app(title=title, version=version)

    # ----- Public API -------------------------------------------------------

    def on_transcript(self, func: TranscriptHandler) -> TranscriptHandler:
        """Register a handler invoked after each finalized transcript."""
        self._transcript_handlers.append(func)
        return func

    async def dispatch_transcript(self, text: str, ctx: SessionContext) -> None:
        for handler in self._transcript_handlers:
            try:
                await handler(text, ctx)
            except Exception:
                logger.exception("transcript handler raised; continuing")

    def asgi(self) -> FastAPI:
        """Return the underlying FastAPI app (for uvicorn or TestClient)."""
        return self.app

    def run(self, host: str | None = None, port: int | None = None) -> None:
        """Run via uvicorn. Intended for demos; use a proper ASGI server in prod."""
        import uvicorn

        uvicorn.run(
            self.app,
            host=host or self.settings.voxcore_host,
            port=port or self.settings.voxcore_port,
            log_level=self.settings.voxcore_log_level.lower(),
        )

    # ----- Internal ---------------------------------------------------------

    def _build_app(self, *, title: str, version: str) -> FastAPI:
        from ..database import init_db
        from ..routers import auth as auth_router
        from ..routers import gateway as gateway_router
        from ..routers import health as health_router

        app = FastAPI(title=title, version=version)

        # Stash facade on app.state so routers can reach it without globals.
        app.state.voxcore = self

        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.allowed_origins_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

        @app.on_event("startup")
        async def _startup() -> None:
            init_db()

        app.include_router(health_router.router)
        app.include_router(auth_router.router)
        app.include_router(gateway_router.router)
        return app


# ----- Adapter resolution ---------------------------------------------------

def _resolve_asr(ref: str | ASRAdapter | None) -> ASRAdapter | None:
    if ref is None or isinstance(ref, ASRAdapter):
        return ref  # type: ignore[return-value]
    from ..adapters.asr import get_asr_adapter

    return get_asr_adapter(ref)


def _resolve_llm(ref: str | LLMAdapter | None) -> LLMAdapter | None:
    if ref is None or isinstance(ref, LLMAdapter):
        return ref  # type: ignore[return-value]
    from ..adapters.llm import get_llm_adapter

    return get_llm_adapter(ref)


def _resolve_vision(ref: str | VisionAdapter | None) -> VisionAdapter | None:
    if ref is None or isinstance(ref, VisionAdapter):
        return ref  # type: ignore[return-value]
    from ..adapters.vision import get_vision_adapter

    return get_vision_adapter(ref)
