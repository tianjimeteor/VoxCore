"""Voice-assistant example — real LLM, echo ASR for demo purposes.

Set ``DEEPSEEK_API_KEY`` in your ``.env`` (or swap ``llm="openai"``/``"siliconflow"``)
and run::

    python examples/voice_assistant/app.py
"""
from __future__ import annotations

from voxcore import VoxCore

app = VoxCore(asr="echo", llm="deepseek")

SYSTEM_PROMPT = (
    "You are a concise, helpful voice assistant. Answer in one or two sentences. "
    "If asked to perform actions (open apps, send email), explain you cannot yet."
)


@app.on_transcript
async def handler(text: str, ctx) -> None:  # type: ignore[no-untyped-def]
    async for chunk in ctx.llm.complete(text, system=SYSTEM_PROMPT, max_tokens=200):
        await ctx.send(chunk)


if __name__ == "__main__":
    app.run()
