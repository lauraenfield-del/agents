"""Tests for ConversationalAgent.chat (Input -> Plan -> Act -> Review loop)."""
from unittest.mock import MagicMock

from core.runtime.conversational import ConversationalAgent
from core.tools.manager import ToolManager


def _make_agent(model_responses: list[str]) -> ConversationalAgent:
    agent = ConversationalAgent(name="TestAgent")
    mock_model = MagicMock()
    mock_model.generate.side_effect = model_responses
    agent.model = mock_model
    return agent


def _make_agent_with_tools(model_responses: list[str]) -> tuple[ConversationalAgent, ToolManager]:
    agent = _make_agent(model_responses)

    tool_manager = MagicMock(spec=ToolManager)
    tool_manager.list_tools.return_value = ["echo"]
    tool_manager.get_tool_schema.return_value = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "additionalProperties": False,
    }
    tool_manager.execute_tool.return_value = "echo result"
    agent.tools = tool_manager

    return agent, tool_manager


class TestChatNoTools:
    def test_returns_model_response_directly(self):
        agent = _make_agent(["answer"])
        response = agent.chat("hello")

        assert response == "answer"
        assert agent.model.generate.call_count == 1

    def test_empty_input_returns_prompt(self):
        agent = _make_agent([])
        result = agent.chat("   ")
        assert "Please provide" in result
        agent.model.generate.assert_not_called()


class TestStructuredToolCalls:
    def test_valid_tool_call_executes_tool(self):
        first = '{"plan":"use tool","tool_calls":[{"tool":"echo","args":{}}],"final_response":""}'
        second = '{"plan":"done","tool_calls":[],"final_response":"final answer"}'
        agent, tool_manager = _make_agent_with_tools([first, second])
        response = agent.chat("use the echo tool")

        tool_manager.execute_tool.assert_called_once_with("echo")
        assert response == "final answer"

    def test_tool_call_with_args(self):
        first = '{"plan":"use tool","tool_calls":[{"tool":"echo","args":{"message":"hi"}}],"final_response":""}'
        second = '{"plan":"done","tool_calls":[],"final_response":"final answer"}'
        agent, tool_manager = _make_agent_with_tools([first, second])
        agent.chat("echo hi")

        tool_manager.execute_tool.assert_called_once_with("echo", message="hi")

    def test_tool_name_is_normalized(self):
        first = '{"plan":"use tool","tool_calls":[{"tool":"ECHO","args":{}}],"final_response":""}'
        second = '{"plan":"done","tool_calls":[],"final_response":"final answer"}'
        agent, tool_manager = _make_agent_with_tools([first, second])
        agent.chat("ECHO test")

        tool_manager.execute_tool.assert_called_once_with("echo")

    def test_unknown_tool_does_not_crash(self):
        first = '{"plan":"use tool","tool_calls":[{"tool":"missing","args":{}}],"final_response":""}'
        second = '{"plan":"done","tool_calls":[],"final_response":"answer"}'
        agent, tool_manager = _make_agent_with_tools([first, second])
        response = agent.chat("something")

        tool_manager.execute_tool.assert_not_called()
        assert response == "answer"

    def test_invalid_json_response_falls_back_to_review_prompt(self):
        agent, _tool_manager = _make_agent_with_tools(["not json", "review answer"])
        response = agent.chat("plain question")

        assert response == "review answer"
        assert agent.model.generate.call_count == 2
