"""Model factory.

Selects the best available real model based on environment variables.
Resolution order:

1. ``OPENAI_API_KEY``  → :class:`OpenAIModel`
2. ``ANTHROPIC_API_KEY`` → :class:`AnthropicModel`
3. Raises ``RuntimeError`` if no key is configured.

The factory is the recommended way to obtain a model inside production code.
Use ``MockModel`` only in tests and the demo script.
"""
from __future__ import annotations

import os

from core.interfaces.agent import Model


def create_model(system_prompt: str = "You are a helpful AI assistant.") -> Model:
    """Return a real :class:`Model` instance based on the available API keys.

    Parameters
    ----------
    system_prompt:
        Optional system-level instruction forwarded to the underlying LLM.

    Raises
    ------
    RuntimeError
        When neither ``OPENAI_API_KEY`` nor ``ANTHROPIC_API_KEY`` is set.
    ImportError
        When the required SDK package is not installed.
    """
    if os.getenv("OPENAI_API_KEY"):
        from core.model.openai import OpenAIModel
        return OpenAIModel(system_prompt=system_prompt)

    if os.getenv("ANTHROPIC_API_KEY"):
        from core.model.anthropic import AnthropicModel
        return AnthropicModel(system_prompt=system_prompt)

    raise RuntimeError(
        "No LLM API key is configured. "
        "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable real model inference."
    )
