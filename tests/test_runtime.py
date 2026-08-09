import pytest
from unittest.mock import Mock, call
from core.runtime.agent import AgentRuntime
from core.interfaces.agent import Agent, Memory, Model
from core.events.bus import EventBus
from core.tools.manager import ToolManager

@pytest.fixture
def mock_agent():
    # Mock the agent and its properties
    agent = Mock(spec=Agent)
    agent.tools = None
    agent.memory = None
    agent.model = None
    return agent

@pytest.fixture
def mock_event_bus():
    return Mock(spec=EventBus)

@pytest.fixture
def mock_tool_manager():
    return Mock(spec=ToolManager)

@pytest.fixture
def mock_memory():
    return Mock(spec=Memory)

@pytest.fixture
def mock_model():
    return Mock(spec=Model)

def test_runtime_initialization(mock_agent, mock_event_bus, mock_tool_manager, mock_memory, mock_model):
    runtime = AgentRuntime(
        agent=mock_agent, 
        event_bus=mock_event_bus, 
        tool_manager=mock_tool_manager, 
        memory=mock_memory,
        model=mock_model
    )
    assert runtime.agent is mock_agent
    assert runtime.event_bus is mock_event_bus
    assert runtime.tool_manager is mock_tool_manager
    assert runtime.memory is mock_memory
    assert runtime.model is mock_model
    assert mock_agent.tools is mock_tool_manager
    assert mock_agent.memory is mock_memory
    assert mock_agent.model is mock_model

def test_runtime_start_lifecycle(mock_agent, mock_event_bus, mock_tool_manager, mock_memory, mock_model):
    mock_agent.run.return_value = "done"
    runtime = AgentRuntime(
        agent=mock_agent, 
        event_bus=mock_event_bus, 
        tool_manager=mock_tool_manager, 
        memory=mock_memory,
        model=mock_model
    )
    result = runtime.start()
    assert result is True

    mock_agent.run.assert_called_once()

    expected_calls = [
        call("runtime.start"),
        call("agent.run.before"),
        call("agent.run.after"),
        call("runtime.stop"),
    ]
    mock_event_bus.publish.assert_has_calls(expected_calls)

def test_runtime_handles_agent_exception(mock_agent, mock_event_bus, mock_tool_manager, mock_memory, mock_model):
    error = Exception("Something went wrong")
    mock_agent.run.side_effect = error

    runtime = AgentRuntime(
        agent=mock_agent, 
        event_bus=mock_event_bus, 
        tool_manager=mock_tool_manager, 
        memory=mock_memory,
        model=mock_model
    )
    runtime.start()

    mock_agent.run.assert_called_once()

    expected_calls = [
        call("runtime.start"),
        call("agent.run.before"),
        call("agent.error", error),
        call("runtime.stop"),
    ]
    mock_event_bus.publish.assert_has_calls(expected_calls)


def test_runtime_start_returns_false_on_exception(mock_agent, mock_event_bus, mock_tool_manager, mock_memory, mock_model):
    mock_agent.run.side_effect = Exception("failure")
    runtime = AgentRuntime(
        agent=mock_agent,
        event_bus=mock_event_bus,
        tool_manager=mock_tool_manager,
        memory=mock_memory,
        model=mock_model,
    )
    result = runtime.start()
    assert result is False


def test_runtime_can_reraise_agent_exception(mock_agent, mock_event_bus, mock_tool_manager, mock_memory, mock_model):
    error = Exception("Something went wrong")
    mock_agent.run.side_effect = error

    runtime = AgentRuntime(
        agent=mock_agent,
        event_bus=mock_event_bus,
        tool_manager=mock_tool_manager,
        memory=mock_memory,
        model=mock_model,
    )

    with pytest.raises(Exception, match="Something went wrong"):
        runtime.start(raise_exceptions=True)
