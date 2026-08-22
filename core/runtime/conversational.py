"""Conversational agent with an Input → Plan → Act → Review loop."""
from __future__ import annotations

import json
from typing import Any

from core.interfaces.agent import Agent
from core.logging.logger import get_logger

_MAX_ACTION_STEPS = 4

_ACTION_RESPONSE_SHAPE = {
    "plan": "brief plan for this step",
    "tool_calls": [{"tool": "tool_name", "args": {"arg_name": "value"}}],
    "final_response": "set this when no more tool calls are needed",
}


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

        if self.tools is None or not self.tools.list_tools():
            response = self.model.generate(user_input)
            self._logger.debug("Response: %s", response)
            return response

        transcript: list[dict[str, Any]] = []
        for _ in range(_MAX_ACTION_STEPS):
            decision_prompt = self._build_action_prompt(user_input, transcript)
            decision_raw = self.model.generate(decision_prompt)
            self._logger.debug("Decision: %s", decision_raw)
            decision = self._parse_action_response(decision_raw)
            tool_calls = self._normalise_tool_calls(decision.get("tool_calls"))

            if tool_calls:
                results = self._execute_tool_calls(tool_calls)
                transcript.append(
                    {
                        "plan": decision.get("plan", ""),
                        "tool_calls": tool_calls,
                        "tool_results": results,
                    }
                )
                continue

            final_response = decision.get("final_response")
            if isinstance(final_response, str) and final_response.strip():
                self._logger.debug("Response: %s", final_response)
                return final_response.strip()
            break

        review_prompt = self._build_review_prompt(user_input, transcript)
        final_response = self.model.generate(review_prompt)
        self._logger.debug("Response: %s", final_response)
        return final_response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_action_prompt(self, user_input: str, transcript: list[dict[str, Any]]) -> str:
        assert self.tools is not None
        tool_specs = []
        for tool_name in self.tools.list_tools():
            tool_specs.append(
                {
                    "name": tool_name,
                    "schema": self.tools.get_tool_schema(tool_name),
                }
            )

        prompt = (
            "You are in an Input->Plan->Act->Review loop.\n"
            "Decide the next action and respond with JSON only.\n"
            f"JSON shape: {json.dumps(_ACTION_RESPONSE_SHAPE)}\n"
            "Rules:\n"
            "1) Use tool_calls only when needed.\n"
            "2) Every tool call must reference a listed tool and conform to its schema.\n"
            "3) If no tools are needed, return tool_calls as [] and provide final_response.\n"
            f"Available tools: {json.dumps(tool_specs)}\n"
            f"User request: {user_input}\n"
        )
        if transcript:
            prompt += f"Previous tool transcript: {json.dumps(transcript)}\n"
        return prompt

    def _build_review_prompt(self, user_input: str, transcript: list[dict[str, Any]]) -> str:
        return (
            "Use the tool transcript to answer the user naturally and clearly.\n"
            f"User request: {user_input}\n"
            f"Tool transcript: {json.dumps(transcript)}\n"
            "Provide only the final answer for the user."
        )

    @staticmethod
    def _parse_action_response(response_text: str) -> dict[str, Any]:
        try:
            parsed = json.loads(response_text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            first = response_text.find("{")
            last = response_text.rfind("}")
            if first == -1 or last == -1 or last <= first:
                return {}
            try:
                parsed = json.loads(response_text[first:last + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}

    @staticmethod
    def _normalise_tool_calls(raw_tool_calls: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_tool_calls, list):
            return []

        normalised: list[dict[str, Any]] = []
        for item in raw_tool_calls:
            if not isinstance(item, dict):
                continue
            tool_name = item.get("tool")
            args = item.get("args", {})
            if not isinstance(tool_name, str) or not tool_name.strip():
                continue
            if not isinstance(args, dict):
                continue
            normalised.append({"tool": tool_name.strip().lower(), "args": args})
        return normalised

    def _execute_tool_calls(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, str]]:
        assert self.tools is not None
        results: list[dict[str, str]] = []
        known_tools = set(self.tools.list_tools())

        for call in tool_calls:
            tool_name = call["tool"]
            args = call["args"]
            if tool_name not in known_tools:
                results.append({"tool": tool_name, "result": "Error: unknown tool"})
                continue
            try:
                self._logger.info("Executing tool: %s", tool_name)
                result = self.tools.execute_tool(tool_name, **args)
                results.append({"tool": tool_name, "result": str(result)})
            except Exception as exc:  # noqa: BLE001
                self._logger.warning("Tool execution failed: %s", exc)
                results.append({"tool": tool_name, "result": f"Error: {exc}"})
        return results
