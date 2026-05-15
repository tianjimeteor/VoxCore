"""Audio capture for VoxNote — same approach as VoxStream but tracks
microphone-only by default since meetings work over the system mic + the call
software's own audio mix.

Set ``VOXNOTE_AUDIO_DEVICE`` to override (e.g. ``"BlackHole 2ch"`` on macOS).
"""
from __future__ import annotations

import asyncio
import logging
import os
import platform
import queue
import threading
from typing import Optional

logger = logging.getLogger("voxnote.recorder")

SAMPLE_RATE = 16_000
CHANNELS = 1
CHUNK_MS = 100


class RecorderUnavailable(RuntimeError):
    """Raised when the OS has no usable audio backend."""


class Recorder:
    """Threaded async audio recorder; identical contract to VoxStream's AudioCapture."""

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._q: queue.Queue[bytes] = queue.Queue(maxsize=128)
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._target = self._select_backend()
        self._thread = threading.Thread(target=self._target, daemon=True, name="voxnote-recorder")
        self._thread.start()

    async def read(self) -> bytes | None:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._q.get, True, 0.5)
        except queue.Empty:
            return None

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _select_backend(self):
        device = os.environ.get("VOXNOTE_AUDIO_DEVICE")
        try:
            return self._make_sounddevice(device)
        except RecorderUnavailable:
            if platform.system() == "Windows":
                return self._make_wasapi(device)
            raise

    def _make_sounddevice(self, device: str | None):
        try:
            import sounddevice as sd  # type: ignore
        except ImportError as err:
            raise RecorderUnavailable("sounddevice not installed") from err

        def run() -> None:
            chunk_frames = int(SAMPLE_RATE * CHUNK_MS / 1000)
            try:
                with sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=chunk_frames,
                    device=device,
                ) as stream:
                    while not self._stop.is_set():
                        if self._paused.is_set():
                            self._stop.wait(0.05)
                            continue
                        data, _ = stream.read(chunk_frames)
                        if self._q.full():
                            try:
                                self._q.get_nowait()
                            except queue.Empty:
                                pass
                        self._q.put_nowait(bytes(data))
            except Exception:  # noqa: BLE001
                logger.exception("sounddevice capture failed")

        return run

    def _make_wasapi(self, device: str | None):
        try:
            import pyaudiowpatch as pa  # type: ignore
        except ImportError as err:
            raise RecorderUnavailable("pyaudiowpatch missing") from err

        def run() -> None:
            p = pa.PyAudio()
            try:
                target = p.get_default_wasapi_loopback()
                stream = p.open(
                    format=pa.paInt16,
                    channels=1,
                    rate=SAMPLE_RATE,
                    frames_per_buffer=int(SAMPLE_RATE * CHUNK_MS / 1000),
                    input=True,
                    input_device_index=target["index"],
                )
                while not self._stop.is_set():
                    if self._paused.is_set():
                        self._stop.wait(0.05)
                        continue
                    chunk = stream.read(int(SAMPLE_RATE * CHUNK_MS / 1000), exception_on_overflow=False)
                    if self._q.full():
                        try:
                            self._q.get_nowait()
                        except queue.Empty:
                            pass
                    self._q.put_nowait(chunk)
                stream.stop_stream()
                stream.close()
            finally:
                p.terminate()

        return run
