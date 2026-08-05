import os
from core.interfaces.agent import Tool

class FileSystemTool(Tool):
    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "A tool to interact with the filesystem. Can read and write files."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["read", "write"]},
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Content to write to the file. Required for write operation."},
            },
            "required": ["operation", "path"],
            "if": {
                "properties": { "operation": { "const": "write" } }
            },
            "then": {
                "required": ["content"]
            }
        }

    def execute(self, operation: str, path: str, content: str = None):
        if operation == "read":
            return self._read_file(path)
        elif operation == "write":
            if content is None:
                raise ValueError("Content must be provided for write operation.")
            return self._write_file(path, content)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _read_file(self, path: str) -> str:
        if not os.path.exists(path):
            return f"Error: File not found at {path}"
        with open(path, 'r') as f:
            return f.read()

    def _write_file(self, path: str, content: str) -> str:
        try:
            with open(path, 'w') as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing to file: {e}"
