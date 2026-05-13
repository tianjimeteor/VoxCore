"""Abstract base for multimodal vision adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod


class VisionAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def describe(self, image_bytes: bytes, prompt: str = "Describe this image.") -> str:
        """Return a single-shot description of an image."""
        raise NotImplementedError
