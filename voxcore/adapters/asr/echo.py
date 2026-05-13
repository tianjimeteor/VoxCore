"""Echo ASR — does no real recognition, just emits a fixed transcript per chunk.

Used by tests and the `minimal_echo` example so contributors can run the stack
without any third-party credentials.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from .base import ASRAdapter, Transcript


class EchoASR(ASRAdapter):
    name = "echo"

    async def stream(
        self, audio: AsyncIterator[bytes]
    ) -> AsyncIterator[Transcript]:
        count = 0
        async for _chunk in audio:
            count += 1
            if count % 10 == 0:
                yield Transcript(text=f"[echo {count} chunks]", is_final=True)
