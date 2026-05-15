"""Optional local Whisper backend for VoxNote.

Uses `faster-whisper` (CTranslate2) — about 4x faster than the reference
``openai-whisper``, and ships pure Python wheels. Models are downloaded on
first use into ``%LOCALAPPDATA%/voxnote/models/`` (or ``~/.local/share`` on
Linux/macOS), giving users an offline path without baking 1+ GB into the
installer.

This module only registers a VoxCore ASR adapter; the rest of VoxNote sees it
as any other adapter named ``"whisper-local"``.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import platform
import wave
from collections.abc import AsyncIterator
from pathlib import Path

from voxcore.adapters.asr import register_asr_adapter
from voxcore.adapters.asr.base import ASRAdapter, Transcript

logger = logging.getLogger("voxnote.whisper_local")


def _models_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "voxnote" / "models"
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "voxnote" / "models"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "voxnote" / "models"
    base.mkdir(parents=True, exist_ok=True)
    return base


class LocalWhisperASR(ASRAdapter):
    """Buffer audio for ~3s, then transcribe with faster-whisper.

    Streaming-style real-time decoding with Whisper requires VAD + chunk
    overlap; this v0 implementation goes for accuracy over latency by
    accumulating short windows. Good enough for meeting notes.
    """

    name = "whisper-local"
    WINDOW_SECONDS = 3.0
    SAMPLE_RATE = 16_000

    def __init__(self, model_size: str = "base", language: str | None = None) -> None:
        self.model_size = model_size
        self.language = language
        self._model = None  # lazy

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as err:
            raise RuntimeError(
                "faster-whisper not installed. `pip install voxnote[local]`"
            ) from err
        logger.info("loading faster-whisper %s into %s", self.model_size, _models_dir())
        self._model = WhisperModel(
            self.model_size,
            device="auto",
            compute_type="int8",
            download_root=str(_models_dir()),
        )
        return self._model

    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        buf = bytearray()
        target_bytes = int(self.SAMPLE_RATE * self.WINDOW_SECONDS) * 2  # 16-bit mono
        async for chunk in audio:
            buf.extend(chunk)
            while len(buf) >= target_bytes:
                window = bytes(buf[:target_bytes])
                del buf[:target_bytes]
                text, conf = await asyncio.get_running_loop().run_in_executor(
                    None, self._transcribe, window
                )
                if text:
                    yield Transcript(text=text, is_final=True, confidence=conf)

    def _transcribe(self, pcm16: bytes) -> tuple[str, float | None]:
        wav = io.BytesIO()
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.SAMPLE_RATE)
            w.writeframes(pcm16)
        wav.seek(0)
        model = self._load()
        segments, _info = model.transcribe(
            wav,
            language=self.language,
            vad_filter=True,
            beam_size=1,
        )
        parts: list[str] = []
        confidences: list[float] = []
        for seg in segments:
            parts.append(seg.text.strip())
            if seg.avg_logprob is not None:
                confidences.append(float(seg.avg_logprob))
        text = " ".join(p for p in parts if p)
        conf = sum(confidences) / len(confidences) if confidences else None
        return text, conf


def register() -> None:
    """Idempotently register the local Whisper adapter with voxcore."""
    register_asr_adapter("whisper-local", LocalWhisperASR)


# Register on import so ``voxnote`` users can ``--asr whisper-local`` immediately.
try:  # pragma: no cover
    register()
except Exception:  # noqa: BLE001
    logger.debug("whisper-local registration failed", exc_info=True)
