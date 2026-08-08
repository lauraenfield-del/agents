"""Tests for ConversationalAgent.chat (Input → Plan → Act → Review loop)."""
import json
import pytest
from unittest.mock import MagicMock, patch

from core.runtime.conversational import ConversationalAgent
from core.tools.manager import ToolManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(model_responses: list[str]) -> ConversationalAgent:
    """Return a ConversationalAgent with a mock model that yields *model_responses* in order."""
    agent = ConversationalAgent(name="TestAgent")

    mock_model = MagicMock()
    mock_model.generate.side_effect = model_responses
    agent.model = mock_model

    return agent


def _make_agent_with_tools(model_responses: list[str]) -> tuple[ConversationalAgent, ToolManager]:
    """Return an agent whose tools include a simple echo tool."""
    agent = _make_agent(model_responses)

    tool_manager = MagicMock(spec=ToolManager)
    tool_manager.list_tools.return_value = ["echo"]
    tool_manager.execute_tool.return_value = "echo result"
    agent.tools = tool_manager

    return agent, tool_manager


# ---------------------------------------------------------------------------
# No-tool path
# ---------------------------------------------------------------------------

class TestChatNoTools:
    def test_returns_plan_response_directly(self):
        """When no tools are invoked, the plan response is returned without a second LLM call."""
        agent = _make_agent(["plan answer"])
        response = agent.chat("hello")

        assert response == "plan answer"
        # Only one generate() call for the plan; no redundant second call.
        assert agent.model.generate.call_count == 1

    def test_empty_input_returns_prompt(self):
        agent = _make_agent([])
        result = agent.chat("   ")
        assert "Please provide" in result
        agent.model.generate.assert_not_called()


# ---------------------------------------------------------------------------
# Tool directive parsing
# ---------------------------------------------------------------------------

class TestToolDirectiveParsing:
    def test_valid_directive_executes_tool(self):
        """A valid TOOL: directive causes the tool to be executed."""
        plan = "TOOL:echo ARGS:{}"
        agent, tool_manager = _make_agent_with_tools([plan, "final answer"])
        response = agent.chat("use the echo tool")

        tool_manager.execute_tool.assert_called_once_with("echo")
        assert response == "final answer"

    def test_directive_with_json_args(self):
        """Args JSON is parsed and forwarded to execute_tool as kwargs."""
        plan = 'TOOL:echo ARGS:{"message": "hi"}'
        agent, tool_manager = _make_agent_with_tools([plan, "final answer"])
        agent.chat("echo hi")

        tool_manager.execute_tool.assert_called_once_with("echo", message="hi")

    def test_case_insensitive_tool_name(self):
        """Tool names in directives are normalised to lower-case before lookup."""
        plan = "TOOL:ECHO ARGS:{}"
        agent, tool_manager = _make_agent_with_tools([plan, "final answer"])
        agent.chat("ECHO test")

        tool_manager.execute_tool.assert_called_once_with("echo")

    def test_unknown_tool_directive_is_skipped(self):
        """Unknown tool directives are silently skipped; no crash and no review call."""
        plan = "TOOL:does_not_exist ARGS:{}"
        agent, tool_manager = _make_agent_with_tools([plan, "answer"])
        # Should not raise; unknown tools produce no results, so no review call either.
        response = agent.chat("something")
        tool_manager.execute_tool.assert_not_called()
        # plan_response is returned directly; no second generate() call
        assert agent.model.generate.call_count == 1

    def test_malformed_args_directive_is_skipped(self):
        """Malformed JSON in ARGS does not crash the agent."""
        plan = "TOOL:echo ARGS:{bad json}"
        agent, tool_manager = _make_agent_with_tools([plan, "answer"])
        response = agent.chat("something")
        tool_manager.execute_tool.assert_not_called()


# ---------------------------------------------------------------------------
# Tool execution + review prompt
# ---------------------------------------------------------------------------

class TestChatWithTools:
    def test_review_call_uses_tool_results(self):
        """After tool execution, a second generate() is called with the tool results."""
        plan = "TOOL:echo ARGS:{}"
        agent, tool_manager = _make_agent_with_tools([plan, "reviewed answer"])
        response = agent.chat("run echo")

        assert agent.model.generate.call_count == 2
        review_prompt = agent.model.generate.call_args[0][0]
        assert "echo result" in review_prompt
        assert "run echo" in review_prompt
        assert response == "reviewed answer"

    def test_no_tool_path_uses_plan_response_not_second_call(self):
        """No-tool path returns plan_response, confirming no extra generate() call."""
        agent = _make_agent(["plan only"])
        agent.tools = MagicMock(spec=ToolManager)
        agent.tools.list_tools.return_value = []
        agent.tools.execute_tool.return_value = "never called"

        response = agent.chat("plain question")
        assert response == "plan only"
        assert agent.model.generate.call_count == 1
