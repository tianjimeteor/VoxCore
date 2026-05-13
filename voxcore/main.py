"""ASGI entry point for ``uvicorn voxcore.main:app``.

This builds a default app with echo adapters. Real applications should
construct their own ``VoxCore(...)`` in a user module instead.
"""
from __future__ import annotations

from . import VoxCore

_default = VoxCore(asr="echo", llm="echo", title="VoxCore (default)")
app = _default.asgi()


@_default.on_transcript
async def _default_handler(text: str, ctx) -> None:  # type: ignore[no-untyped-def]
    if ctx.llm is None:
        await ctx.send(text)
        return
    async for chunk in ctx.llm.complete(text):
        await ctx.send(chunk)
