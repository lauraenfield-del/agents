import json
import os
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

from builders.validate_package import validate_package
from core.events.bus import EventBus
from core.interfaces.agent import Model
from core.memory.simple import SimpleMemory
from core.runtime.agent import AgentRuntime
from core.runtime.conversational import ConversationalAgent
from core.tools.filesystem import FileSystemTool
from core.tools.manager import ToolManager
from core.tools.search import WebSearchTool
from core.tools.terminal import TerminalTool
from core.tools.think import SequentialThinkingTool
from core.tools.web import WebFetchTool


def _make_system_prompt(manifest: dict) -> str:
    """Build the system prompt from a package manifest."""
    return (
        f"You are {manifest.get('name', 'an AI agent')}. "
        f"{manifest.get('description', '')} "
        "Answer clearly and helpfully. Follow a practical Input->Plan->Act->Review "
        "flow and use tools when they are needed to satisfy the user request."
    )


class ManifestAgent(ConversationalAgent):
    """Agent loaded from a package manifest.

    Inherits the full :class:`ConversationalAgent` capability so that every
    manifest-driven agent can chat naturally and use the Input→Plan→Act→Review
    loop out of the box.
    """

    def __init__(self, manifest: dict) -> None:
        super().__init__(
            name=manifest.get("name", "Agent"),
            system_prompt=_make_system_prompt(manifest),
        )
        self.manifest = manifest


# ---------------------------------------------------------------------------
# Tool registry helpers
# ---------------------------------------------------------------------------

_TOOL_REGISTRY: dict[str, type] = {
    "filesystem": FileSystemTool,
    "web_fetch": WebFetchTool,
    "web_search": WebSearchTool,
    "think": SequentialThinkingTool,
    "terminal": TerminalTool,
    # "browser" is an alias for web_fetch for manifest compatibility
    "browser": WebFetchTool,
}


def _search_github_for_tool(tool_name: str, max_results: int = 3) -> list[dict[str, str]]:
    """Search GitHub for public repositories that may implement *tool_name*.

    Uses the unauthenticated GitHub Search API (60 req/h).  Returns a list of
    dicts with ``name``, ``html_url``, and ``description`` keys.  Returns an
    empty list on any error so callers can always iterate safely.
    """
    query = urllib.parse.quote_plus(f"agent tool {tool_name} python")
    url = (
        f"https://api.github.com/search/repositories"
        f"?q={query}&sort=stars&order=desc&per_page={max_results}"
    )
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "agents-framework/1.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [
            {
                "name": item.get("full_name", ""),
                "html_url": item.get("html_url", ""),
                "description": item.get("description") or "",
            }
            for item in data.get("items", [])[:max_results]
        ]
    except Exception:  # noqa: BLE001
        return []


def _register_known_tools(tool_manager: ToolManager, tool_names: list[str]) -> None:
    registered: set[str] = set()
    for tool_name in tool_names:
        tool_cls = _TOOL_REGISTRY.get(tool_name)
        if tool_cls is not None:
            instance = tool_cls()
            # Avoid registering duplicate canonical names
            if instance.name not in registered:
                tool_manager.register_tool(instance)
                registered.add(instance.name)
        else:
            msg = (
                f"Manifest references unknown tool '{tool_name}'. "
                "This tool will not be available at runtime. "
                "Check the tool name or register a custom implementation."
            )
            if os.getenv("AGENT_TOOL_SEARCH", "").strip().lower() in ("1", "true", "yes"):
                suggestions = _search_github_for_tool(tool_name)
                if suggestions:
                    lines = [f"  • {s['name']} – {s['html_url']}" for s in suggestions]
                    msg += (
                        "\n  GitHub search found these candidate repositories:\n"
                        + "\n".join(lines)
                    )
                else:
                    msg += "\n  GitHub search returned no results for this tool name."
            warnings.warn(msg, RuntimeWarning, stacklevel=2)


def _build_model(manifest: dict) -> Model:
    """Create the best available real model, falling back with a clear message."""
    try:
        from core.model.factory import create_model
        return create_model(system_prompt=_make_system_prompt(manifest))
    except RuntimeError as exc:
        # No API key configured – inform the operator and use the mock so that
        # the framework is still usable for local testing without credentials.
        warnings.warn(
            f"No LLM API key configured ({exc}). "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY for real model inference. "
            "Falling back to MockModel for now.",
            RuntimeWarning,
            stacklevel=2,
        )
        from core.model.mock import MockModel
        return MockModel()


def build_agent(package_dir: str | Path) -> AgentRuntime:
    manifest = validate_package(package_dir)
    tool_manager = ToolManager()
    _register_known_tools(tool_manager, manifest["tools"])

    return AgentRuntime(
        agent=ManifestAgent(manifest),
        event_bus=EventBus(),
        tool_manager=tool_manager,
        memory=SimpleMemory(),
        model=_build_model(manifest),
    )


def load_registered_packages(
    registry_path: str | Path = Path("registry") / "package_index.json",
) -> dict:
    registry_path = Path(registry_path)
    if not registry_path.exists():
        return {}
    with registry_path.open("r", encoding="utf-8") as registry_file:
        return json.load(registry_file) or {}
