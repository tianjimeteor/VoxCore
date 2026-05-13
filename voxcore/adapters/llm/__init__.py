"""LLM adapter registry."""
from __future__ import annotations

from .base import LLMAdapter
from .echo import EchoLLM
from .openai_compatible import DeepSeekLLM, OpenAILLM, SiliconFlowLLM

_registry: dict[str, type[LLMAdapter]] = {
    "echo": EchoLLM,
    "openai": OpenAILLM,
    "deepseek": DeepSeekLLM,
    "siliconflow": SiliconFlowLLM,
}


def get_llm_adapter(name: str) -> LLMAdapter:
    try:
        cls = _registry[name]
    except KeyError as err:
        raise ValueError(
            f"Unknown LLM adapter {name!r}. Available: {sorted(_registry)}"
        ) from err
    return cls()


def register_llm_adapter(name: str, cls: type[LLMAdapter]) -> None:
    _registry[name] = cls


__all__ = ["LLMAdapter", "get_llm_adapter", "register_llm_adapter"]
