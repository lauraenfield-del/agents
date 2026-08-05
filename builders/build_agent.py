import json
from pathlib import Path

from builders.validate_package import validate_package
from core.events.bus import EventBus
from core.interfaces.agent import Agent, Tool
from core.memory.simple import SimpleMemory
from core.model.mock import MockModel
from core.runtime.agent import AgentRuntime
from core.tools.filesystem import FileSystemTool
from core.tools.manager import ToolManager


class ManifestAgent(Agent):
    def __init__(self, manifest: dict):
        self.manifest = manifest

    def run(self, *args, **kwargs):
        return {
            "name": self.manifest["name"],
            "workflow": self.manifest["entrypoint"]["workflow"],
        }


class _UnknownTool(Tool):
    """Placeholder for manifest tools that have no registered implementation."""

    def __init__(self, tool_name: str):
        self._name = tool_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Unimplemented tool: {self._name}"

    @property
    def schema(self) -> dict:
        return {}

    def execute(self, *args, **kwargs):
        raise NotImplementedError(
            f"Tool '{self._name}' is declared in the manifest but has no registered implementation."
        )


def _register_known_tools(tool_manager: ToolManager, tool_names: list[str]):
    for tool_name in tool_names:
        if tool_name == "filesystem":
            tool_manager.register_tool(FileSystemTool())
        else:
            tool_manager.register_tool(_UnknownTool(tool_name))


def build_agent(package_dir: str | Path) -> AgentRuntime:
    manifest = validate_package(package_dir)
    tool_manager = ToolManager()
    _register_known_tools(tool_manager, manifest["tools"])

    return AgentRuntime(
        agent=ManifestAgent(manifest),
        event_bus=EventBus(),
        tool_manager=tool_manager,
        memory=SimpleMemory(),
        model=MockModel(),
    )


def load_registered_packages(
    registry_path: str | Path = Path("registry") / "package_index.json",
) -> dict:
    registry_path = Path(registry_path)
    if not registry_path.exists():
        return {}
    with registry_path.open("r", encoding="utf-8") as registry_file:
        return json.load(registry_file) or {}