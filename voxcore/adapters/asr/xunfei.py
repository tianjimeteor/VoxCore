"""Xunfei (iFlytek) streaming ASR adapter — placeholder.

This file defines the class surface; the actual WebSocket handshake against
``wss://iat.xf-yun.com/v1`` is deliberately not implemented here to keep the
dependency surface minimal. See ``docs/adapters.md`` for the protocol details
and how to contribute a production implementation.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from ...config import get_settings
from .base import ASRAdapter, Transcript


class XunfeiASR(ASRAdapter):
    name = "xunfei"

    def __init__(self) -> None:
        settings = get_settings()
        if not (
            settings.xunfei_app_id
            and settings.xunfei_api_key
            and settings.xunfei_api_secret
        ):
            raise RuntimeError(
                "Xunfei credentials missing. Set XUNFEI_APP_ID / XUNFEI_API_KEY / "
                "XUNFEI_API_SECRET or pick a different ASR adapter."
            )
        self._app_id = settings.xunfei_app_id
        self._api_key = settings.xunfei_api_key
        self._api_secret = settings.xunfei_api_secret

    async def stream(
        self, audio: AsyncIterator[bytes]
    ) -> AsyncIterator[Transcript]:
        # Production implementation pending; see docs/adapters.md.
        raise NotImplementedError(
            "XunfeiASR stream is a stub in the open-source distribution. "
            "Contribute an implementation — see CONTRIBUTING.md."
        )
        if False:  # pragma: no cover
            yield
