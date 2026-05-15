"""Cross-platform system / mic audio capture.

We try the highest-quality option available on each platform, falling back to a
plain microphone capture or raising :class:`CaptureUnavailable` so the server
can keep serving the overlay even if no audio backend is installed (useful for
HF Space where audio comes from the browser, not the host).

Order of preference:

* Windows: ``pyaudiowpatch`` WASAPI loopback (capture system audio = the user
  speaking *and* anyone in the call). Falls back to default input mic.
* macOS: ``sounddevice`` default input (mic). System audio requires BlackHole;
  if not present we just print a hint.
* Linux: ``sounddevice`` default input. PulseAudio ``monitor`` source can be
  selected via ``VOXSTREAM_AUDIO_DEVICE`` env var.
"""
from __future__ import annotations

import asyncio
import logging
import os
import platform
import queue
import threading
from typing import Optional

logger = logging.getLogger("voxstream.capture")

SAMPLE_RATE = 16_000
CHANNELS = 1
CHUNK_MS = 100  # 100ms chunks → 1.6 KB at 16k mono s16le


class CaptureUnavailable(RuntimeError):
    """Raised when no usable audio backend was found on this machine."""


class AudioCapture:
    """Thin async wrapper around a thread-fed bytes queue."""

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._q: queue.Queue[bytes] = queue.Queue(maxsize=64)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._impl = self._select_backend()
        self._thread = threading.Thread(target=self._impl, daemon=True, name="voxstream-capture")
        self._thread.start()

    async def read(self) -> bytes | None:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._q.get, True, 0.5)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    # -- backend selection ---------------------------------------------------

    def _select_backend(self):
        env_device = os.environ.get("VOXSTREAM_AUDIO_DEVICE")
        system = platform.system()

        if system == "Windows":
            try:
                return self._make_wasapi_loopback(env_device)
            except CaptureUnavailable as err:
                logger.warning("wasapi loopback unavailable (%s); trying default mic", err)
        try:
            return self._make_sounddevice(env_device)
        except CaptureUnavailable as err:
            logger.error("no audio backend: %s", err)
            raise

    def _make_wasapi_loopback(self, device_hint: str | None):
        try:
            import pyaudiowpatch as pyaudio
        except ImportError as err:
            raise CaptureUnavailable("pyaudiowpatch not installed") from err

        def run() -> None:
            p = pyaudio.PyAudio()
            try:
                # Pick default speaker as loopback source.
                default_speaker = p.get_default_wasapi_loopback()
                if device_hint:
                    for i in range(p.get_device_count()):
                        info = p.get_device_info_by_index(i)
                        if device_hint.lower() in info.get("name", "").lower() and info.get("isLoopbackDevice"):
                            default_speaker = info
                            break

                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=SAMPLE_RATE,
                    frames_per_buffer=int(SAMPLE_RATE * CHUNK_MS / 1000),
                    input=True,
                    input_device_index=default_speaker["index"],
                )
                logger.info("WASAPI loopback active: %s", default_speaker.get("name"))
                while not self._stop.is_set():
                    try:
                        data = stream.read(int(SAMPLE_RATE * CHUNK_MS / 1000), exception_on_overflow=False)
                        if self._q.full():
                            self._q.get_nowait()
                        self._q.put_nowait(data)
                    except Exception:  # noqa: BLE001
                        logger.exception("wasapi read failed")
                        break
                stream.stop_stream()
                stream.close()
            finally:
                p.terminate()

        return run

    def _make_sounddevice(self, device_hint: str | None):
        try:
            import sounddevice as sd  # type: ignore
            import numpy as np  # type: ignore
        except ImportError as err:
            raise CaptureUnavailable(f"sounddevice not installed: {err}") from err

        def run() -> None:
            chunk_frames = int(SAMPLE_RATE * CHUNK_MS / 1000)
            try:
                with sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=chunk_frames,
                    device=device_hint,
                ) as stream:
                    logger.info(
                        "sounddevice input active: %s",
                        device_hint or sd.query_devices(kind="input")["name"],
                    )
                    while not self._stop.is_set():
                        data, _overflow = stream.read(chunk_frames)
                        if self._q.full():
                            try:
                                self._q.get_nowait()
                            except queue.Empty:
                                pass
                        self._q.put_nowait(bytes(data))
            except Exception:  # noqa: BLE001
                logger.exception("sounddevice capture failed")

        return run


def probe() -> dict:
    """Diagnostic: return a dict of detected audio backends. Used by the CLI."""
    info: dict = {"platform": platform.system(), "backends": {}}
    try:
        import pyaudiowpatch as pa  # type: ignore

        p = pa.PyAudio()
        try:
            info["backends"]["wasapi_loopback"] = bool(p.get_default_wasapi_loopback())
        finally:
            p.terminate()
    except Exception as err:  # noqa: BLE001
        info["backends"]["wasapi_loopback"] = f"unavailable: {err}"

    try:
        import sounddevice as sd  # type: ignore

        info["backends"]["sounddevice_input"] = sd.query_devices(kind="input")["name"]
    except Exception as err:  # noqa: BLE001
        info["backends"]["sounddevice_input"] = f"unavailable: {err}"
    return info
