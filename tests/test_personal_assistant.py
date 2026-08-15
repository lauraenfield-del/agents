from builders.build_agent import build_agent
from core.memory.simple import SimpleMemory
from core.runtime.personal_assistant import PersonalAssistantAgent


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


def test_personal_assistant_initializes_workspace_snapshot_from_manifest():
    runtime = build_agent("/home/runner/work/agents/agents/packages/personal_assistant")

    snapshot = runtime.memory.retrieve("assistant:workspace")

    assert snapshot["assistant"]["workflow"] == "personal_assistant_controller"
    assert {"sendblue", "shopify", "canva"}.issubset(set(snapshot["tools"]))
    assert any(connector["type"] == "workspace_snapshot" for connector in snapshot["connectors"])
