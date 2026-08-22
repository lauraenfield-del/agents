"""OpenAI model adapter.

Requires the ``openai`` package and a valid ``OPENAI_API_KEY`` environment
variable.  Set ``OPENAI_MODEL`` to override the default model name.
"""
from __future__ import annotations

import os
from typing import List, Dict

from core.interfaces.agent import Model


class OpenAIModel(Model):
    """Thin wrapper around the OpenAI chat-completions API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        system_prompt: str = "You are a helpful AI assistant.",
    ):
        try:
            import openai as _openai  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAIModel. "
                "Install it with: pip install openai"
            ) from exc

        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "No OpenAI API key found. Set the OPENAI_API_KEY environment variable."
            )
        self._client = _openai.OpenAI(api_key=self._api_key)
        self._system_prompt = system_prompt
        self._history: List[Dict[str, str]] = []

    def generate(self, prompt: str) -> str:
        """Generate a response for *prompt*, maintaining conversation history."""
        self._history.append({"role": "user", "content": prompt})
        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        reply = response.choices[0].message.content or ""
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset_history(self) -> None:
        """Clear the in-memory conversation history."""
        self._history = []
