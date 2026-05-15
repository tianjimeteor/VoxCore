"""The transcription + summarization pipeline.

A :class:`Pipeline` owns one in-flight session: it pulls bytes from the
recorder, hands them to the ASR adapter, persists segments, periodically asks
the LLM for an incremental summary, and emits all of this to subscribers
(the UI poll loop reads from these in-memory buffers).
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import AsyncIterator, Callable

from voxcore.adapters.asr import get_asr_adapter
from voxcore.adapters.llm import get_llm_adapter

from .recorder import Recorder, RecorderUnavailable
from .storage import Segment, Storage, Summary

logger = logging.getLogger("voxnote.pipeline")

SUMMARY_INTERVAL_SECONDS = 30.0
TODO_PATTERNS = [
    re.compile(r"(?:i|we|let'?s|we'?ll|i'?ll)\s+(?:will\s+)?([^.\n]{6,120})", re.IGNORECASE),
    re.compile(r"(?:todo|action item|action|action-item)[:\-]\s*([^.\n]{4,160})", re.IGNORECASE),
    re.compile(r"(?:需要|应该|必须|要)([^。\n]{4,80})"),
]


@dataclass
class LiveCaption:
    text: str
    final: bool
    speaker: str | None
    timestamp_ms: int


class Pipeline:
    """One pipeline ≈ one recording session."""

    def __init__(
        self,
        *,
        storage: Storage,
        asr_name: str,
        llm_name: str,
        on_caption: Callable[[LiveCaption], None] | None = None,
        on_summary: Callable[[Summary], None] | None = None,
    ) -> None:
        self.storage = storage
        self.asr_name = asr_name
        self.llm_name = llm_name
        self._asr = get_asr_adapter(asr_name)
        self._llm = get_llm_adapter(llm_name)
        self._on_caption = on_caption
        self._on_summary = on_summary

        self._recorder: Recorder | None = None
        self._task: asyncio.Task | None = None
        self._summary_task: asyncio.Task | None = None
        self._session_id: str | None = None
        self._started_at: float = 0.0
        self._captions: deque[LiveCaption] = deque(maxlen=200)
        self._latest_summary: Summary | None = None
        self._stop = asyncio.Event()

    # -- public --------------------------------------------------------------

    async def start(self, *, title: str) -> str:
        if self._task and not self._task.done():
            raise RuntimeError("pipeline already running")
        try:
            self._recorder = Recorder()
        except RecorderUnavailable as err:
            raise RuntimeError(f"audio capture unavailable: {err}") from err

        sess = self.storage.create_session(
            title=title, asr_name=self.asr_name, llm_name=self.llm_name
        )
        self._session_id = sess.id
        self._started_at = sess.started_at
        self._captions.clear()
        self._stop.clear()
        self._task = asyncio.create_task(self._run_asr())
        self._summary_task = asyncio.create_task(self._run_summary_loop())
        return sess.id

    async def stop(self) -> Summary | None:
        if not self._session_id:
            return None
        self._stop.set()
        if self._recorder:
            self._recorder.close()
        for t in (self._task, self._summary_task):
            if t:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        # Final summary pass.
        final = await self._make_summary(kind="final")
        if final:
            self.storage.upsert_summary(final)
            self._latest_summary = final
            if self._on_summary:
                self._on_summary(final)
        self.storage.end_session(self._session_id)
        sid = self._session_id
        self._session_id = None
        return self._latest_summary

    def captions_snapshot(self) -> list[LiveCaption]:
        return list(self._captions)

    @property
    def latest_summary(self) -> Summary | None:
        return self._latest_summary

    @property
    def session_id(self) -> str | None:
        return self._session_id

    # -- internals -----------------------------------------------------------

    async def _audio_iter(self) -> AsyncIterator[bytes]:
        assert self._recorder is not None
        while not self._stop.is_set():
            chunk = await self._recorder.read()
            if chunk is None:
                continue
            yield chunk

    async def _run_asr(self) -> None:
        if not self._session_id:
            return
        try:
            async for tr in self._asr.stream(self._audio_iter()):
                if not tr.text.strip():
                    continue
                ts_ms = int((time.time() - self._started_at) * 1000)
                cap = LiveCaption(
                    text=tr.text, final=tr.is_final, speaker=None, timestamp_ms=ts_ms
                )
                self._captions.append(cap)
                if self._on_caption:
                    self._on_caption(cap)

                if tr.is_final:
                    self.storage.add_segment(
                        Segment(
                            session_id=self._session_id,
                            start_ms=max(0, ts_ms - 2_000),
                            end_ms=ts_ms,
                            text=tr.text,
                            confidence=tr.confidence,
                        )
                    )
        except asyncio.CancelledError:
            return
        except Exception:  # noqa: BLE001
            logger.exception("asr loop terminated")

    async def _run_summary_loop(self) -> None:
        try:
            while not self._stop.is_set():
                await asyncio.sleep(SUMMARY_INTERVAL_SECONDS)
                summary = await self._make_summary(kind="incremental")
                if summary:
                    self.storage.upsert_summary(summary)
                    self._latest_summary = summary
                    if self._on_summary:
                        self._on_summary(summary)
        except asyncio.CancelledError:
            return

    async def _make_summary(self, *, kind: str) -> Summary | None:
        if not self._session_id:
            return None
        segments = self.storage.list_segments(self._session_id)
        if not segments:
            return None
        joined = "\n".join(s.text for s in segments[-200:])
        prompt = (
            "You are a meeting note assistant. Read the transcript below and write:\n"
            "1. A concise markdown summary (3-6 bullets).\n"
            "2. A 'Action items' list of TODOs (one per line, '- ' prefix). "
            "If none, write '- none'.\n\n"
            f"Transcript:\n{joined}"
        )
        parts: list[str] = []
        try:
            async for chunk in self._llm.complete(prompt, max_tokens=512):
                parts.append(chunk)
        except Exception:  # noqa: BLE001
            logger.exception("llm summary failed")
            parts.append(joined[-500:])  # graceful fallback

        body = "".join(parts).strip()
        todos = _extract_todos(joined, body)
        return Summary(
            session_id=self._session_id,
            kind=kind,
            generated_at=time.time(),
            summary_md=body or "(no summary yet)",
            todos=todos,
        )


def _extract_todos(transcript: str, summary: str) -> list[str]:
    """Pattern-based TODO extraction from transcript + summary text."""
    found: list[str] = []
    seen: set[str] = set()

    def _push(text: str) -> None:
        t = text.strip(" ,.;:-")
        if 4 <= len(t) <= 200 and t.lower() not in seen:
            seen.add(t.lower())
            found.append(t)

    # Summary "Action items" block.
    in_actions = False
    for line in summary.splitlines():
        if re.search(r"action\s*items?", line, re.IGNORECASE):
            in_actions = True
            continue
        if in_actions:
            stripped = line.strip()
            if not stripped:
                in_actions = False
                continue
            if stripped.startswith(("-", "*", "•")):
                _push(stripped.lstrip("-*• "))

    # Pattern fallback (cap 10 hits per pattern to avoid runaway).
    for pat in TODO_PATTERNS:
        for i, m in enumerate(pat.finditer(transcript)):
            if i >= 10:
                break
            _push(m.group(1))

    return found[:20]
