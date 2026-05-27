"""
LLM abstraction layer.

Business code calls get_llm_service().complete(prompt) and never imports
OpenAI or Anthropic directly. Switching providers is a one-line change in
settings: LLM_BACKEND = "openai" | "claude"
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class BaseLLMService(ABC):

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Send a plain-text prompt, return the model's text response."""


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIService(BaseLLMService):

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", max_tokens: int = 2048):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


# ── Claude ────────────────────────────────────────────────────────────────────

class ClaudeService(BaseLLMService):

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = 2048):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


# ── Factory ───────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, type[BaseLLMService]] = {
    "openai": OpenAIService,
    "claude": ClaudeService,
}


def get_llm_service() -> BaseLLMService:
    """
    Read LLM_BACKEND from Django settings, return the matching service.
    Constructor args (api_key, model) are also pulled from settings so
    tasks.py never references provider-specific config directly.
    """
    from django.conf import settings

    backend = getattr(settings, "LLM_BACKEND", "openai")
    cls = _REGISTRY.get(backend)
    if cls is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown LLM_BACKEND '{backend}' in settings. Known: {known}"
        )

    if backend == "openai":
        return cls(
            api_key=settings.OPENAI_API_KEY,
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
        )
    if backend == "claude":
        return cls(
            api_key=settings.ANTHROPIC_API_KEY,
            model=getattr(settings, "ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        )
