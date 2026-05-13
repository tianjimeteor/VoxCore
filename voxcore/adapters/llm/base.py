"""Abstract base for streaming LLM adapters (OpenAI-compatible Chat Completions)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream tokens (as text chunks) for the given prompt."""
        raise NotImplementedError
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]
