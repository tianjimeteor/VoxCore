"""Abstract base for streaming speech-to-text adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class Transcript:
    """One chunk emitted by an ASR stream."""

    text: str
    is_final: bool
    confidence: float | None = None


class ASRAdapter(ABC):
    """Stream 16 kHz mono PCM in, get transcripts out."""

    name: str = "base"

    @abstractmethod
    async def stream(
        self, audio: AsyncIterator[bytes]
    ) -> AsyncIterator[Transcript]:
        """Consume an async audio stream, yield partial + final transcripts."""
        raise NotImplementedError
        if False:  # pragma: no cover — make mypy treat this as an async generator
            yield
