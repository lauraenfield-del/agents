import pytest
from unittest.mock import Mock, call
from core.orchestration.manager import WorkflowManager
from core.orchestration.workflows import SequentialWorkflow
from core.interfaces.agent import Agent, Workflow

@pytest.fixture
def mock_agent():
    agent = Mock(spec=Agent)
    agent.tools = Mock()
    agent.memory = Mock()
    agent.model = Mock()
    return agent

@pytest.fixture
def workflow_manager():
    return WorkflowManager()

def test_workflow_registration(workflow_manager):
    class MyWorkflow(Workflow):
        @property
        def name(self) -> str:
            return "my_workflow"
        def run(self, agent: Agent):
            pass

    workflow = MyWorkflow()
    workflow_manager.register_workflow(workflow)
    # This is an internal detail, but good to test
    assert "my_workflow" in workflow_manager._workflows 

def test_run_sequential_workflow(workflow_manager, mock_agent):
    steps = [
        {"prompt": "This is a test prompt."},
        {"tool_call": {"name": "filesystem", "args": {"operation": "read", "path": "test.txt"}}},
    ]
    workflow = SequentialWorkflow(name="test_workflow", steps=steps)
    workflow_manager.register_workflow(workflow)
    workflow_manager.run_workflow("test_workflow", mock_agent)

    mock_agent.model.generate.assert_called_once_with("This is a test prompt.")
    mock_agent.tools.execute_tool.assert_called_once_with("filesystem", operation="read", path="test.txt")

def test_run_non_existent_workflow(workflow_manager, mock_agent):
    with pytest.raises(ValueError, match="Workflow 'non_existent_workflow' not found."):
        workflow_manager.run_workflow("non_existent_workflow", mock_agent)

def test_register_invalid_workflow(workflow_manager):
    class NotAWorkflow:
        pass

    with pytest.raises(TypeError, match="Workflow must be an instance of the Workflow interface."):
        workflow_manager.register_workflow(NotAWorkflow())
