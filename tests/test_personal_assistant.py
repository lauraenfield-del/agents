from core.memory.simple import SimpleMemory
from core.runtime.personal_assistant import PersonalAssistantAgent


def test_status_without_activity():
    agent = PersonalAssistantAgent(name="PA")
    agent.memory = SimpleMemory()
    result = agent.chat("status")
    assert "No completed actions yet" in result
