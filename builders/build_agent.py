import json
import os
from pathlib import Path

from builders.validate_package import validate_package
from core.events.bus import EventBus
from core.interfaces.agent import Agent
from core.memory.simple import SimpleMemory
from core.model.mock import MockModel
from core.model.openai_compatible import OpenAICompatibleModel
from core.runtime.agent import AgentRuntime
from core.tools.communication import CommunicationTool
from core.tools.filesystem import FileSystemTool
from core.tools.manager import ToolManager
from core.tools.sequential_thinking import SequentialThinkingTool
from core.tools.terminal import TerminalTool
from core.tools.web import WebTool


class ManifestAgent(Agent):
    def __init__(self, manifest: dict):
        self.manifest = manifest

    def run(self, *args, **kwargs):
        user_input = kwargs.get("user_input")
        if user_input is None and args:
            user_input = args[0]
        if not user_input:
            raise ValueError("ManifestAgent requires non-empty user_input.")

        available_tools = ", ".join(self.tools.list_tools()) if self.tools else "none"
        plan_prompt = (
            f"You are {self.manifest['name']}. "
            "Create a short plan with clear numbered steps for the user request below. "
            "Reference which tools you would use when relevant.\n\n"
            f"Available tools: {available_tools}\n"
            f"User request: {user_input}"
        )
        plan = self.model.generate(plan_prompt)
        self.memory.store("last_user_input", user_input)
        self.memory.store("last_plan", plan)

        action_results = []
        tool_calls = kwargs.get("tool_calls") or []
        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            if not tool_name:
                continue
            try:
                action_results.append(
                    {
                        "tool": tool_name,
                        "result": self.tools.execute_tool(tool_name, **tool_args),
                    }
                )
            except Exception as exc:
                action_results.append({"tool": tool_name, "error": str(exc)})

        self.memory.store("last_actions", action_results)
        review_prompt = (
            "Using the plan and tool results below, answer the user conversationally. "
            "Be direct, factual, and helpful.\n\n"
            f"Original request: {user_input}\n"
            f"Plan:\n{plan}\n\n"
            f"Tool results: {action_results}"
        )
        final_response = self.model.generate(review_prompt)
        self.memory.store("last_response", final_response)
        return final_response


TOOL_ALIASES = {
    "filesystem": "filesystem",
    "terminal": "terminal",
    "web": "web",
    "browser": "web",
    "scraper": "web",
    "knowledge_base": "web",
    "communication": "communication",
    "email": "communication",
    "ticketing_system": "communication",
    "social_posting": "communication",
    "sequential_thinking": "sequential_thinking",
}


def _register_known_tools(tool_manager: ToolManager, tool_names: list[str]):
    builtins = {
        "filesystem": FileSystemTool(),
        "terminal": TerminalTool(),
        "web": WebTool(),
        "communication": CommunicationTool(),
        "sequential_thinking": SequentialThinkingTool(),
    }
    enabled = set()
    for tool_name in tool_names:
        normalized = TOOL_ALIASES.get(tool_name)
        if normalized is None:
            raise ValueError(
                f"Tool '{tool_name}' is declared in the manifest but no implementation is available."
            )
        if normalized not in enabled:
            tool_manager.register_tool(builtins[normalized])
            enabled.add(normalized)


def _build_model():
    if os.getenv("AGENTS_USE_MOCK_MODEL", "").lower() in {"1", "true", "yes"}:
        return MockModel()
    return OpenAICompatibleModel()


def build_agent(package_dir: str | Path) -> AgentRuntime:
    manifest = validate_package(package_dir)
    tool_manager = ToolManager()
    _register_known_tools(tool_manager, manifest["tools"])

    return AgentRuntime(
        agent=ManifestAgent(manifest),
        event_bus=EventBus(),
        tool_manager=tool_manager,
        memory=SimpleMemory(),
        model=_build_model(),
    )


def load_registered_packages(
    registry_path: str | Path = Path("registry") / "package_index.json",
) -> dict:
    registry_path = Path(registry_path)
    if not registry_path.exists():
        return {}
    with registry_path.open("r", encoding="utf-8") as registry_file:
        return json.load(registry_file) or {}
