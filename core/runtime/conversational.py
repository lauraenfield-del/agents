"""Conversational agent with an Input → Plan → Act → Review loop.

This module provides :class:`ConversationalAgent`, a concrete :class:`Agent`
implementation that drives a natural-language chat loop powered by the
configured model and tools.

The loop follows the standard agentic pattern:

1. **Input**  – accept a user message.
2. **Plan**   – ask the model to think about what to do.
3. **Act**    – optionally invoke tools suggested by the model.
4. **Review** – ask the model to refine its answer given tool results.
5. Return the final response to the caller.
"""
from __future__ import annotations

from typing import Any

from core.interfaces.agent import Agent
from core.logging.logger import get_logger

_PLAN_SUFFIX = (
    "\n\nBefore responding, briefly outline your plan: what you intend to do "
    "and which tools (if any) you will use."
)

_REVIEW_PREFIX = (
    "Based on the following tool results, provide a clear, natural-language "
    "response to the user:\n\n"
)


class ConversationalAgent(Agent):
    """An agent that responds to free-form natural-language input.

    The agent maintains its own turn history and drives the
    Input → Plan → Act → Review cycle on each call to :meth:`chat`.
    """

    def __init__(self, name: str = "Agent", system_prompt: str | None = None) -> None:
        self._name = name
        self._system_prompt = system_prompt
        self._logger = get_logger(name)

    # ------------------------------------------------------------------
    # Agent interface
    # ------------------------------------------------------------------

    def run(self, user_input: str = "", **kwargs: Any) -> str:
        """Single-turn entrypoint.  Delegates to :meth:`chat`."""
        return self.chat(user_input)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, user_input: str) -> str:
        """Process *user_input* and return the agent's response.

        The method follows Input → Plan → Act → Review:

        1. The model is asked to plan its response.
        2. Any tool calls embedded in the plan are executed.
        3. The model reviews tool results and produces the final answer.
        """
        if not user_input.strip():
            return "Please provide a message to continue the conversation."

        self._logger.debug("User: %s", user_input)

        # ── 1. Plan ──────────────────────────────────────────────────
        plan_prompt = user_input + _PLAN_SUFFIX
        plan_response = self.model.generate(plan_prompt)
        self._logger.debug("Plan: %s", plan_response)

        # ── 2. Act (tool invocation) ──────────────────────────────────
        tool_results = self._try_execute_tools(plan_response)

        # ── 3. Review ────────────────────────────────────────────────
        if tool_results:
            review_prompt = (
                _REVIEW_PREFIX
                + "\n\n".join(f"[{name}]: {result}" for name, result in tool_results)
                + f"\n\nUser's original request: {user_input}"
            )
            final_response = self.model.generate(review_prompt)
        else:
            # No tools used; the plan response already answers the user.
            final_response = self.model.generate(user_input)

        self._logger.debug("Response: %s", final_response)
        return final_response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_execute_tools(self, plan_text: str) -> list[tuple[str, str]]:
        """Parse simple ``TOOL:<name> ARGS:<json>`` directives from the plan.

        The model is expected to emit lines like::

            TOOL:web_search ARGS:{"query": "Python asyncio"}

        This is a lightweight, regex-free parser – robust enough for typical
        LLM output without adding heavyweight parsing dependencies.
        """
        if self.tools is None:
            return []

        results: list[tuple[str, str]] = []
        import json as _json

        for line in plan_text.splitlines():
            line = line.strip()
            if not line.upper().startswith("TOOL:"):
                continue
            try:
                after_tool = line[5:]  # strip "TOOL:"
                if " ARGS:" in after_tool.upper():
                    split_idx = after_tool.upper().index(" ARGS:")
                    tool_name = after_tool[:split_idx].strip()
                    args_str = after_tool[split_idx + 6:].strip()
                    args = _json.loads(args_str)
                else:
                    tool_name = after_tool.strip()
                    args = {}

                if tool_name in self.tools.list_tools():
                    self._logger.info("Executing tool: %s", tool_name)
                    result = self.tools.execute_tool(tool_name, **args)
                    results.append((tool_name, str(result)))
            except Exception as exc:  # noqa: BLE001
                self._logger.warning("Tool execution failed: %s", exc)

        return results
