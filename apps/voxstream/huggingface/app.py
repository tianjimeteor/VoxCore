"""HF Space entry point for VoxStream.

Hugging Face Spaces auto-runs a top-level ``app.py``. We wrap VoxStream's
caption pipeline behind a Gradio UI so anyone can open the URL and see
captions in their browser without installing anything.

Note: HF Space sandboxes the host audio device. We accept browser-recorded
audio via ``gr.Audio(sources=["microphone"], streaming=True)`` instead of the
desktop capture backend.
"""
from __future__ import annotations

import asyncio
import io
import os
import wave
from collections.abc import AsyncIterator

import gradio as gr  # type: ignore
import numpy as np  # type: ignore

from voxcore.adapters.asr import get_asr_adapter

ASR_NAME = os.environ.get("VOXSTREAM_ASR", "echo")
asr = get_asr_adapter(ASR_NAME)

EXAMPLES = [
    "Add this URL as an OBS Browser Source for free live captions.",
    "VoxStream is the demo. VoxCore is the engine. Both are Apache-2.0.",
]


def _to_pcm16(audio_tuple) -> bytes:
    """gradio gives (sample_rate, np.int16 array). Resample naively to 16 kHz mono."""
    if audio_tuple is None:
        return b""
    sr, data = audio_tuple
    if data.ndim > 1:
        data = data.mean(axis=1).astype(np.int16)
    if sr != 16000:
        # Crude, dependency-free linear resample. Good enough for a demo.
        ratio = 16000 / float(sr)
        new_len = int(len(data) * ratio)
        if new_len <= 0:
            return b""
        idx = np.linspace(0, len(data) - 1, num=new_len).astype(np.int64)
        data = data[idx].astype(np.int16)
    return data.tobytes()


async def _stream_once(pcm: bytes) -> AsyncIterator[bytes]:
    # Hand the bytes to the ASR adapter as a single-chunk stream.
    if pcm:
        yield pcm


async def _transcribe(pcm: bytes) -> str:
    parts: list[str] = []
    async for tr in asr.stream(_stream_once(pcm)):
        parts.append(tr.text)
    return " ".join(parts).strip() or "(no speech detected)"


def transcribe_sync(audio):
    pcm = _to_pcm16(audio)
    return asyncio.run(_transcribe(pcm))


with gr.Blocks(title="VoxStream — live caption demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # VoxStream live caption demo
        Real-time captions for OBS streamers / lecturers / meetings,
        powered by [VoxCore](https://github.com/tianjimeteor/VoxCore).
        Apache-2.0. Self-host the desktop version for your own stream.

        **How:** click the mic, talk for a few seconds, release. The output box
        shows what VoxStream would have pushed to your OBS overlay.
        """
    )
    with gr.Row():
        mic = gr.Audio(sources=["microphone"], type="numpy", label="Speak")
        out = gr.Textbox(label="Caption", lines=4)
    mic.stop_recording(transcribe_sync, inputs=mic, outputs=out)
    gr.Examples(EXAMPLES, inputs=out)
    gr.Markdown(
        f"ASR adapter currently in use: **`{ASR_NAME}`**. "
        "Set the `VOXSTREAM_ASR` env var on this Space to switch (e.g. `xunfei`)."
    )


if __name__ == "__main__":
    demo.launch()
