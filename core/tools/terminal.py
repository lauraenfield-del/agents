"""Terminal tool.

Runs a shell command in a subprocess and returns its combined stdout/stderr.

Safety controls:
* Commands are executed with a configurable timeout (default 30 s).
* A configurable allow-list (``AGENT_TERMINAL_ALLOW_CMDS`` env var,
  space-separated) can restrict which command prefixes are permitted.
  When the env var is not set, any command is allowed.
* The working directory defaults to the current directory but can be
  overridden per call via the ``cwd`` parameter.
"""
from __future__ import annotations

import os
import subprocess

from core.interfaces.agent import Tool


class TerminalTool(Tool):
    """Executes a shell command and returns the output."""

    @property
    def name(self) -> str:
        return "terminal"

    @property
    def description(self) -> str:
        return (
            "Run a shell command and return its output (stdout + stderr). "
            "Use for file operations, running scripts, installing packages, etc."
        )

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command. Defaults to current directory.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds. Defaults to 30.",
                },
            },
            "required": ["command"],
        }

    def execute(self, command: str, cwd: str | None = None, timeout: int = 30) -> str:
        allow_env = os.getenv("AGENT_TERMINAL_ALLOW_CMDS", "").strip()
        if allow_env:
            allowed = allow_env.split()
            first_token = command.strip().split()[0] if command.strip() else ""
            if first_token not in allowed:
                return (
                    f"Command '{first_token}' is not in the allowed command list. "
                    f"Allowed: {', '.join(allowed)}"
                )

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            output = result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr
            if result.returncode != 0:
                output = f"[exit {result.returncode}]\n" + output
            return output.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds."
        except Exception as exc:
            return f"Error running command: {exc}"
