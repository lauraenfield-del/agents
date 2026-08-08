"""Sequential thinking tool.

Provides structured, step-by-step reasoning support.  The tool records a chain
of *thoughts* in memory and returns a formatted reasoning trace.

This tool does **not** call an external LLM; it is a local, deterministic
helper that agents can use to break a problem into explicit steps before acting.
When the agent's model is available it can be combined with prompts, but the
tool itself is self-contained and works without any API key.
"""
from __future__ import annotations

from typing import List, Dict

from core.interfaces.agent import Tool


class SequentialThinkingTool(Tool):
    """Records and returns a chain-of-thought reasoning trace."""

    def __init__(self) -> None:
        self._chain: List[Dict[str, str]] = []

    @property
    def name(self) -> str:
        return "think"

    @property
    def description(self) -> str:
        return (
            "Break a problem into sequential reasoning steps. "
            "Use 'add' to append a thought, 'review' to see the full chain, "
            "and 'reset' to start fresh."
        )

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "review", "reset"],
                    "description": "Operation: 'add' a thought, 'review' all thoughts, 'reset' the chain.",
                },
                "thought": {
                    "type": "string",
                    "description": "The reasoning step to record. Required when action is 'add'.",
                },
            },
            "required": ["action"],
            "if": {"properties": {"action": {"const": "add"}}},
            "then": {"required": ["thought"]},
        }

    def execute(self, action: str, thought: str = "") -> str:
        if action == "add":
            if not thought:
                raise ValueError("'thought' is required when action is 'add'.")
            step = len(self._chain) + 1
            self._chain.append({"step": step, "thought": thought})
            return f"Step {step} recorded: {thought}"

        if action == "review":
            if not self._chain:
                return "No thoughts recorded yet."
            lines = [f"Step {item['step']}: {item['thought']}" for item in self._chain]
            return "Reasoning chain:\n" + "\n".join(lines)

        if action == "reset":
            count = len(self._chain)
            self._chain = []
            return f"Reasoning chain cleared ({count} step(s) removed)."

        raise ValueError(f"Unknown action: '{action}'. Use 'add', 'review', or 'reset'.")
