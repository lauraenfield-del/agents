import pytest
import os
from core.tools.manager import ToolManager
from core.tools.filesystem import FileSystemTool

@pytest.fixture
def tool_manager():
    return ToolManager()

@pytest.fixture
def filesystem_tool():
    return FileSystemTool()

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
