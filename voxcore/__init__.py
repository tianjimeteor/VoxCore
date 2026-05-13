"""VoxCore — the open real-time voice AI engine.

Public API:

    from voxcore import VoxCore, stream

See README.md for usage.
"""
from __future__ import annotations

from .core.facade import VoxCore
from .core.streaming import stream

__all__ = ["VoxCore", "stream", "__version__"]
__version__ = "0.1.0"
