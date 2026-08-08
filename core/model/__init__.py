"""core.model – LLM provider adapters and model factory.

Available adapters
------------------
* :class:`~core.model.mock.MockModel`       – deterministic stub (tests / demo only)
* :class:`~core.model.openai.OpenAIModel`   – OpenAI chat-completions API
* :class:`~core.model.anthropic.AnthropicModel` – Anthropic messages API

Recommended usage in production code
--------------------------------------
Use :func:`~core.model.factory.create_model` which auto-selects the best
available provider based on the environment::

    from core.model.factory import create_model
    model = create_model()
"""
from core.model.mock import MockModel

__all__ = ["MockModel"]
