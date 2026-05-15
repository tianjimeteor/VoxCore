"""Streaming helpers.

`stream(...)` is a thin adapter so user-facing examples can treat anything that
yields text as an async iterable of chunks — strings, generators, coroutines
that return iterables, etc. It exists so the 20-line demo in the README can
`async for chunk in stream(...)` without worrying about the underlying shape.
"""
from __future__ import annotations

import inspect
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Iterable
from typing import Union

_StreamLike = Union[  # noqa: UP007 -- explicit Union keeps this multiline alias readable
    str,
    Iterable[str],
    AsyncIterable[str],
    Awaitable["_StreamLike"],
]


async def stream(source: _StreamLike) -> AsyncIterator[str]:
    """Normalize anything string-ish into `async for chunk in ...`.

    Examples::

        async for chunk in stream("hello"):         # single string → one chunk
            ...
        async for chunk in stream(["a", "b"]):       # sync iterable → chunks
            ...
        async for chunk in stream(llm.complete(q)): # awaitable of iterable
            ...
    """
    if inspect.isawaitable(source):
        source = await source  # type: ignore[assignment]

    if isinstance(source, str):
        yield source
        return

    if hasattr(source, "__aiter__"):
        async for chunk in source:  # type: ignore[union-attr]
            yield chunk
        return

    if hasattr(source, "__iter__"):
        for chunk in source:  # type: ignore[union-attr]
            yield chunk
        return

    raise TypeError(f"stream() does not support {type(source)!r}")
