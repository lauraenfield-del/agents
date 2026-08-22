from typing import Dict, List
from core.interfaces.agent import Tool
from core.validation.validator import Validator

class ToolManager:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool):
        if not isinstance(tool, Tool):
            raise TypeError("Tool must be an instance of the Tool interface.")
        self._tools[tool.name] = tool

    def execute_tool(self, name: str, *args, **kwargs):
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")
        
        tool = self._tools[name]
        Validator.validate(kwargs, tool.schema)

        return tool.execute(*args, **kwargs)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_tool_schema(self, name: str) -> dict:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")
        return self._tools[name].schema

    def get_tool(self, name: str) -> Tool:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")
        return self._tools[name]
