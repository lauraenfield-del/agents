"""Anthropic model adapter.

Requires the ``anthropic`` package and a valid ``ANTHROPIC_API_KEY``
environment variable.  Set ``ANTHROPIC_MODEL`` to override the default model.
"""
from __future__ import annotations

import os
from typing import List, Dict

from core.interfaces.agent import Model


class AnthropicModel(Model):
    """Thin wrapper around the Anthropic messages API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        system_prompt: str = "You are a helpful AI assistant.",
    ):
        try:
            import anthropic as _anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicModel. "
                "Install it with: pip install anthropic"
            ) from exc

        self._model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "No Anthropic API key found. Set the ANTHROPIC_API_KEY environment variable."
            )
        self._client = _anthropic.Anthropic(api_key=self._api_key)
        self._system_prompt = system_prompt
        self._history: List[Dict[str, str]] = []

    def generate(self, prompt: str) -> str:
        """Generate a response for *prompt*, maintaining conversation history."""
        self._history.append({"role": "user", "content": prompt})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=self._system_prompt,
            messages=self._history,
        )
        reply = (response.content[0].text if response.content else "") or ""
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset_history(self) -> None:
        """Clear the in-memory conversation history."""
        self._history = []
