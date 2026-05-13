"""`stream()` normalizes the various shapes a user handler can return."""
from __future__ import annotations

import pytest

from voxcore import stream


async def _collect(src) -> list[str]:  # type: ignore[no-untyped-def]
    return [c async for c in stream(src)]


@pytest.mark.asyncio
async def test_stream_string() -> None:
    assert await _collect("hello") == ["hello"]


@pytest.mark.asyncio
async def test_stream_iterable() -> None:
    assert await _collect(["a", "b", "c"]) == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_stream_async_iterable() -> None:
    async def gen():
        for x in ["x", "y"]:
            yield x

    assert await _collect(gen()) == ["x", "y"]


@pytest.mark.asyncio
async def test_stream_unsupported_type_raises() -> None:
    with pytest.raises(TypeError):
        await _collect(12345)  # type: ignore[arg-type]
