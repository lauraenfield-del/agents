from pathlib import Path

from builders.build_agent import build_agent
from core.interfaces.agent import Tool
from core.memory.simple import SimpleMemory
from core.tools.manager import ToolManager
from core.runtime.personal_assistant import PersonalAssistantAgent


class _ApprovalTool(Tool):
    def __init__(self):
        self.calls = []

    @property
    def name(self) -> str:
        return "sendblue"

    @property
    def description(self) -> str:
        return "Approval test tool."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "approved": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def execute(self, action: str, approved: bool = False) -> dict:
        self.calls.append({"action": action, "approved": approved})
        return {"status": "ok", "approved": approved}


def test_status_without_activity():
    agent = PersonalAssistantAgent(name="PA")
    agent.memory = SimpleMemory()
    result = agent.chat("status")
    assert "No completed actions yet" in result


def test_status_snapshot_stores_only_redacted_response_metadata():
    agent = PersonalAssistantAgent(name="PA")
    agent.memory = SimpleMemory()

    agent._update_status_snapshot("api_key=super-secret")

    assert agent.memory.retrieve("assistant:last_response_redacted") == {
        "redacted": True,
        "preview": "[redacted]",
        "length": len("api_key=super-secret"),
    }


def test_execute_tool_calls_replaces_stale_pending_queue_when_empty():
    agent = PersonalAssistantAgent(name="PA")
    agent.memory = SimpleMemory()
    agent.memory.store(agent._PENDING_KEY, [{"tool": "sendblue", "args": {}, "approval_token": "oldtoken123456"}])
    manager = ToolManager()
    manager.register_tool(_ApprovalTool())
    agent.tools = manager

    agent._execute_tool_calls([{"tool": "sendblue", "args": {"action": "list_threads"}}])

    assert agent.memory.retrieve(agent._PENDING_KEY) == []


def test_execute_tool_calls_queues_gated_actions_before_execution():
    agent = PersonalAssistantAgent(name="PA")
    agent.memory = SimpleMemory()
    tool = _ApprovalTool()
    manager = ToolManager()
    manager.register_tool(tool)
    agent.tools = manager

    results = agent._execute_tool_calls(
        [{"tool": "sendblue", "args": {"action": "send_message", "approved": True}}]
    )

    assert tool.calls == []
    pending = agent.memory.retrieve(agent._PENDING_KEY)
    assert len(pending) == 1
    assert pending[0]["tool"] == "sendblue"
    assert pending[0]["args"] == {"action": "send_message"}
    assert "approve " in results[0]["result"]


def test_execute_tool_calls_preserves_pending_within_active_turn():
    agent = PersonalAssistantAgent(name="PA")
    agent.memory = SimpleMemory()
    tool = _ApprovalTool()
    manager = ToolManager()
    manager.register_tool(tool)
    agent.tools = manager
    agent._pending_turn = []

    agent._execute_tool_calls([{"tool": "sendblue", "args": {"action": "send_message"}}])
    agent._execute_tool_calls([{"tool": "sendblue", "args": {"action": "list_threads"}}])

    pending = agent.memory.retrieve(agent._PENDING_KEY)
    assert len(pending) == 1
    assert pending[0]["tool"] == "sendblue"
    del agent._pending_turn


def test_chat_approval_executes_matching_pending_request():
    agent = PersonalAssistantAgent(name="PA")
    agent.memory = SimpleMemory()
    tool = _ApprovalTool()
    manager = ToolManager()
    manager.register_tool(tool)
    agent.tools = manager
    token = agent._approval_token("sendblue", {"action": "send_message"})
    agent.memory.store(
        agent._PENDING_KEY,
        [{"tool": "sendblue", "args": {"action": "send_message"}, "approval_token": token}],
    )

    response = agent.chat(f"approve {token}")

    assert "Approved action completed for sendblue" in response
    assert tool.calls == [{"action": "send_message", "approved": True}]
    assert agent.memory.retrieve(agent._PENDING_KEY) == []


def test_personal_assistant_initializes_workspace_snapshot_from_manifest():
    runtime = build_agent(Path(__file__).parent.parent / "packages" / "personal_assistant")

    snapshot = runtime.memory.retrieve("assistant:workspace")

    assert snapshot["assistant"]["workflow"] == "personal_assistant_controller"
    assert {"sendblue", "shopify", "canva"}.issubset(set(snapshot["tools"]))
    assert any(connector["type"] == "workspace_snapshot" for connector in snapshot["connectors"])
