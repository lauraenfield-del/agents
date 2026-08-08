import subprocess

from core.interfaces.agent import Tool


class TerminalTool(Tool):
    @property
    def name(self) -> str:
        return "terminal"

    @property
    def description(self) -> str:
        return "Runs shell commands and returns stdout/stderr with the exit code."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout_seconds": {"type": "number", "minimum": 1, "maximum": 120},
            },
            "required": ["command"],
            "additionalProperties": False,
        }

    def execute(self, command: str, cwd: str | None = None, timeout_seconds: float = 30):
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
