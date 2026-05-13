"""OpenAI-compatible streaming chat adapters.

DeepSeek, SiliconFlow, Moonshot, Zhipu, Together, Groq, many local servers —
they all speak the OpenAI Chat Completions schema. One adapter, many providers.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from ...config import get_settings
from .base import LLMAdapter


class _OpenAICompatible(LLMAdapter):
    default_model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"

    def __init__(
        self, *, api_key: str, base_url: str | None = None, model: str | None = None
    ) -> None:
        if not api_key:
            raise RuntimeError(
                f"{self.__class__.__name__} requires an API key. "
                "Set the corresponding *_API_KEY environment variable."
            )
        self._api_key = api_key
        self._base_url = (base_url or self.base_url).rstrip("/")
        self._model = model or self.default_model

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for raw in resp.aiter_lines():
                    if not raw or not raw.startswith("data:"):
                        continue
                    data = raw[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if delta:
                        yield delta


class OpenAILLM(_OpenAICompatible):
    name = "openai"
    default_model = "gpt-4o-mini"

    def __init__(self) -> None:
        s = get_settings()
        super().__init__(api_key=s.openai_api_key, base_url=s.openai_base_url)


class DeepSeekLLM(_OpenAICompatible):
    name = "deepseek"
    default_model = "deepseek-chat"

    def __init__(self) -> None:
        s = get_settings()
        super().__init__(api_key=s.deepseek_api_key, base_url=s.deepseek_base_url)


class SiliconFlowLLM(_OpenAICompatible):
    name = "siliconflow"
    default_model = "Qwen/Qwen2.5-7B-Instruct"

    def __init__(self) -> None:
        s = get_settings()
        super().__init__(api_key=s.siliconflow_api_key, base_url=s.siliconflow_base_url)
