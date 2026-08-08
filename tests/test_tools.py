import pytest
import os
from core.tools.manager import ToolManager
from core.tools.communication import CommunicationTool
from core.tools.filesystem import FileSystemTool
from core.tools.sequential_thinking import SequentialThinkingTool
from core.tools.terminal import TerminalTool
from core.tools.web import WebTool

@pytest.fixture
def tool_manager():
    return ToolManager()

@pytest.fixture
def filesystem_tool():
    return FileSystemTool()

@pytest.fixture
def terminal_tool():
    return TerminalTool()

@pytest.fixture
def sequential_tool():
    return SequentialThinkingTool()

@pytest.fixture
def web_tool():
    return WebTool()

@pytest.fixture
def communication_tool():
    return CommunicationTool()

def test_tool_registration(tool_manager, filesystem_tool):
    tool_manager.register_tool(filesystem_tool)
    assert "filesystem" in tool_manager.list_tools()

def test_get_tool_schema(tool_manager, filesystem_tool):
    tool_manager.register_tool(filesystem_tool)
    schema = tool_manager.get_tool_schema("filesystem")
    assert schema is not None
    assert schema["type"] == "object"

def test_filesystem_tool_read_and_write(tool_manager, filesystem_tool):
    tool_manager.register_tool(filesystem_tool)
    test_file_path = "test_file.txt"
    test_content = "Hello, world!"

    # Clean up before test
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    # Test write
    write_result = tool_manager.execute_tool("filesystem", operation="write", path=test_file_path, content=test_content)
    assert "Successfully wrote" in write_result
    assert os.path.exists(test_file_path)

    # Test read
    read_result = tool_manager.execute_tool("filesystem", operation="read", path=test_file_path)
    assert read_result == test_content

    # Clean up after test
    os.remove(test_file_path)

def test_execute_non_existent_tool(tool_manager):
    with pytest.raises(ValueError, match="Tool 'non_existent_tool' not found."):
        tool_manager.execute_tool("non_existent_tool")

def test_execute_tool_with_invalid_args(tool_manager, filesystem_tool):
    tool_manager.register_tool(filesystem_tool)
    with pytest.raises(ValueError, match="'path' is a required property"):
        tool_manager.execute_tool("filesystem", operation="read") # Missing path

def test_execute_write_with_missing_content(tool_manager, filesystem_tool):
    tool_manager.register_tool(filesystem_tool)
    with pytest.raises(ValueError, match="'content' is a required property"):
        tool_manager.execute_tool("filesystem", operation="write", path="test.txt")

def test_register_invalid_tool(tool_manager):
    class NotATool:
        pass

    with pytest.raises(TypeError, match="Tool must be an instance of the Tool interface."):
        tool_manager.register_tool(NotATool())


def test_terminal_tool_executes_command(tool_manager, terminal_tool, monkeypatch):
    monkeypatch.setenv("AGENT_TERMINAL_ALLOW_CMDS", "echo")
    tool_manager.register_tool(terminal_tool)
    result = tool_manager.execute_tool("terminal", command="echo hello")
    assert "hello" in result


def test_sequential_thinking_tracks_steps(tool_manager, sequential_tool):
    tool_manager.register_tool(sequential_tool)
    append_result = tool_manager.execute_tool(
        "sequential_thinking", session_id="s1", operation="append", thought="First step"
    )
    assert append_result["steps"] == ["First step"]

    list_result = tool_manager.execute_tool("sequential_thinking", session_id="s1", operation="list")
    assert list_result["steps"] == ["First step"]


def test_web_tool_fetches_and_strips_html(tool_manager, web_tool, monkeypatch):
    class DummyResponse:
        status = 200
        headers = {"Content-Type": "text/html"}

        def read(self, size=-1):
            return b"<html><body><h1>Title</h1><p>hello world</p></body></html>"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyOpener:
        def open(self, *args, **kwargs):
            return DummyResponse()

    monkeypatch.setattr("core.tools.web._build_ssrf_safe_opener", lambda: DummyOpener())
    tool_manager.register_tool(web_tool)
    result = tool_manager.execute_tool("web_fetch", url="https://example.com")
    assert "Title" in result
    assert "hello world" in result


def test_communication_webhook_success(tool_manager, communication_tool, monkeypatch):
    class DummyResponse:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyOpener:
        def open(self, *args, **kwargs):
            return DummyResponse()

    monkeypatch.setattr(
        "core.tools.communication.build_ssrf_safe_opener", lambda: DummyOpener()
    )
    tool_manager.register_tool(communication_tool)
    result = tool_manager.execute_tool(
        "communication",
        channel="webhook",
        target="https://example.com/webhook",
        message="hello",
    )
    assert result["status"] == "sent"
