"""Minimal echo example — the shortest possible VoxCore app.

No third-party credentials required. Run with::

    python -m voxcore.cli gen-secret > .env
    python examples/minimal_echo/app.py

Then open ``examples/web_demo/index.html`` in a browser.
"""
from __future__ import annotations

from voxcore import VoxCore, stream

app = VoxCore(asr="echo", llm="echo")


@app.on_transcript
async def handler(text: str, ctx) -> None:  # type: ignore[no-untyped-def]
    async for chunk in stream(f"You said: {text}. This is an echo reply."):
        await ctx.send(chunk)


if __name__ == "__main__":
    app.run()
