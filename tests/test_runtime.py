import pytest
from unittest.mock import Mock, call
from core.runtime.agent import AgentRuntime
from core.interfaces.agent import Agent
from core.events.bus import EventBus

@pytest.fixture
def mock_agent():
    return Mock(spec=Agent)

@pytest.fixture
def mock_event_bus():
    return Mock(spec=EventBus)

def test_runtime_initialization(mock_agent, mock_event_bus):
    runtime = AgentRuntime(agent=mock_agent, event_bus=mock_event_bus)
    assert runtime.agent is mock_agent
    assert runtime.event_bus is mock_event_bus

def test_runtime_start_lifecycle(mock_agent, mock_event_bus):
    runtime = AgentRuntime(agent=mock_agent, event_bus=mock_event_bus)
    runtime.start()

    mock_agent.run.assert_called_once()

    expected_calls = [
        call("runtime.start"),
        call("agent.run.before"),
        call("agent.run.after"),
        call("runtime.stop"),
    ]
    mock_event_bus.publish.assert_has_calls(expected_calls)

def test_runtime_handles_agent_exception(mock_agent, mock_event_bus):
    error = Exception("Something went wrong")
    mock_agent.run.side_effect = error

    runtime = AgentRuntime(agent=mock_agent, event_bus=mock_event_bus)
    runtime.start()

    mock_agent.run.assert_called_once()

    expected_calls = [
        call("runtime.start"),
        call("agent.run.before"),
        call("agent.error", error),
        call("runtime.stop"),
    ]
    mock_event_bus.publish.assert_has_calls(expected_calls)
