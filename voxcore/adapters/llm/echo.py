"""Echo LLM — returns the input. Lets contributors run everything without API keys."""
from __future__ import annotations

from collections.abc import AsyncIterator

from .base import LLMAdapter


class EchoLLM(LLMAdapter):
    name = "echo"

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,  # noqa: ARG002
        max_tokens: int = 512,  # noqa: ARG002
        temperature: float = 0.7,  # noqa: ARG002
    ) -> AsyncIterator[str]:
        for word in prompt.split():
            yield word + " "
