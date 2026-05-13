# Writing an Adapter

All adapters are ordinary Python classes registered in a small in-memory table.
The minimum viable adapter is ~30 lines.

## LLM adapter

```python
# voxcore/adapters/llm/my_provider.py
from collections.abc import AsyncIterator
import httpx
from .base import LLMAdapter
from ...config import get_settings

class MyProviderLLM(LLMAdapter):
    name = "myprovider"
    default_model = "my-model-7b"

    def __init__(self) -> None:
        s = get_settings()
        if not s.myprovider_api_key:
            raise RuntimeError("MYPROVIDER_API_KEY not set")
        self._key = s.myprovider_api_key

    async def complete(self, prompt, *, system=None, max_tokens=512, temperature=0.7):
        # yield str chunks; the framework takes care of the rest
        async with httpx.AsyncClient() as c:
            async with c.stream("POST", "https://...", json={...}) as r:
                async for line in r.aiter_lines():
                    yield ...
```

Then register it:

```python
# voxcore/adapters/llm/__init__.py
from .my_provider import MyProviderLLM
_registry["myprovider"] = MyProviderLLM
```

Most OpenAI-compatible providers do not need a new class at all — subclass
`_OpenAICompatible` and set `name`, `default_model`, `base_url`.

## ASR adapter

Implement `stream(audio_iter)` as an async generator of `Transcript(text, is_final)`.

## Vision adapter

Implement `describe(image_bytes, prompt) -> str`.

## Testing

- Mock the HTTP layer with `httpx.MockTransport` — no live network in CI.
- Add a test under `tests/adapters/test_<name>.py` that exercises the happy path
  and at least one error case (invalid API key, malformed stream).
- Update the adapter table in `README.md` and `README.zh-CN.md`.

## Publishing third-party adapters

Third parties can publish adapters as separate PyPI packages. Register on import
via `register_llm_adapter("name", MyAdapter)`. Open a PR to add your adapter to
the table in [README.md](../README.md).
