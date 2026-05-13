"""ASR adapter registry."""
from __future__ import annotations

from .base import ASRAdapter, Transcript
from .echo import EchoASR

_registry: dict[str, type[ASRAdapter]] = {
    "echo": EchoASR,
}

try:  # Xunfei needs credentials; registration is still safe — construction fails fast.
    from .xunfei import XunfeiASR

    _registry["xunfei"] = XunfeiASR
except ImportError:  # pragma: no cover
    pass


def get_asr_adapter(name: str) -> ASRAdapter:
    try:
        cls = _registry[name]
    except KeyError as err:
        raise ValueError(
            f"Unknown ASR adapter {name!r}. Available: {sorted(_registry)}"
        ) from err
    return cls()


def register_asr_adapter(name: str, cls: type[ASRAdapter]) -> None:
    """Third-party packages can register via this function or a setuptools entry point."""
    _registry[name] = cls


__all__ = ["ASRAdapter", "Transcript", "get_asr_adapter", "register_asr_adapter"]
