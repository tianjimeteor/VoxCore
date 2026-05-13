"""Vision adapter registry."""
from __future__ import annotations

from .base import VisionAdapter

_registry: dict[str, type[VisionAdapter]] = {}


def get_vision_adapter(name: str) -> VisionAdapter:
    try:
        cls = _registry[name]
    except KeyError as err:
        raise ValueError(
            f"Unknown Vision adapter {name!r}. Available: {sorted(_registry)}"
        ) from err
    return cls()


def register_vision_adapter(name: str, cls: type[VisionAdapter]) -> None:
    _registry[name] = cls


__all__ = ["VisionAdapter", "get_vision_adapter", "register_vision_adapter"]
