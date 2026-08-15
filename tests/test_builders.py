import json
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from builders.build_agent import (
    _register_known_tools,
    _search_github_for_tool,
    build_agent,
    load_registered_packages,
)
from builders.generate_package import generate_package
from builders.register_package import register_package
from builders.validate_package import load_package_manifest, validate_package
from core.runtime.agent import AgentRuntime
from core.tools.manager import ToolManager

PACKAGES_DIR = Path(__file__).parent.parent / "packages"


def test_validate_package_existing_manifest():
    manifest = validate_package(PACKAGES_DIR / "autonomous")
    assert manifest["name"] == "Autonomous Agent"
    assert manifest["entrypoint"]["workflow"] == "autonomous_controller"


def test_register_package_updates_registry(tmp_path):
    registry_path = tmp_path / "package_index.json"

    entry = register_package(
        PACKAGES_DIR / "coding",
        registry_path=registry_path,
    )

    assert entry["name"] == "Coding Agent"
    with registry_path.open("r", encoding="utf-8") as registry_file:
        registry = json.load(registry_file)
    assert "coding" in registry


def test_build_agent_creates_runtime_with_known_tools():
    runtime = build_agent(PACKAGES_DIR / "autonomous")

    assert isinstance(runtime, AgentRuntime)
    assert "filesystem" in runtime.tool_manager.list_tools()


def test_build_personal_assistant_registers_integration_tools():
    runtime = build_agent(PACKAGES_DIR / "personal_assistant")
    names = set(runtime.tool_manager.list_tools())
    assert {"sendblue", "shopify", "canva"}.issubset(names)
    assert runtime.agent.__class__.__name__ == "ManifestPersonalAssistantAgent"


def test_build_agent_registers_manifest_import_tool_without_registry_edit(tmp_path):
    package_dir = tmp_path / "imported_tool_agent"
    manifest = {
        "name": "Imported Tool Agent",
        "version": "1.0.0",
        "inherits": "core",
        "description": "Agent with declarative tool import",
        "tools": [{"name": "filesystem", "import": "core.tools.filesystem:FileSystemTool"}],
        "workflows": ["planning"],
        "knowledge": ["docs"],
        "entrypoint": {"workflow": "planning"},
    }
    generate_package(package_dir, manifest)

    runtime = build_agent(package_dir)

    assert "filesystem" in runtime.tool_manager.list_tools()


def test_validate_package_accepts_mapping_tool_specs(tmp_path):
    package_dir = tmp_path / "tool_spec_agent"
    package_dir.mkdir()
    generate_package(
        package_dir,
        {
            "name": "Spec Agent",
            "version": "1.0.0",
            "inherits": "core",
            "description": "Package with mapping tool spec",
            "tools": [{"name": "filesystem", "import": "core.tools.filesystem:FileSystemTool"}],
            "workflows": ["planning"],
            "knowledge": ["docs"],
            "entrypoint": {"workflow": "planning"},
        },
    )

    manifest = validate_package(package_dir)

    assert manifest["tools"][0]["import"] == "core.tools.filesystem:FileSystemTool"


def test_generate_package_writes_manifest(tmp_path):
    package_dir = tmp_path / "generated_agent"
    manifest = {
        "name": "Generated Agent",
        "version": "1.0.0",
        "inherits": "core",
        "description": "Generated package",
        "tools": ["filesystem"],
        "workflows": ["planning"],
        "knowledge": ["docs"],
        "entrypoint": {"workflow": "generated_controller"},
    }

    manifest_path = generate_package(package_dir, manifest)

    assert manifest_path.exists()
    assert load_package_manifest(package_dir)["name"] == "Generated Agent"


def test_validate_package_rejects_missing_fields(tmp_path):
    package_dir = tmp_path / "broken_agent"
    package_dir.mkdir()
    generate_package(package_dir, {"name": "Broken Agent"})

    with pytest.raises(ValueError, match="missing required field: version"):
        validate_package(package_dir)


def test_validate_package_rejects_tool_mapping_without_name(tmp_path):
    package_dir = tmp_path / "broken_tool_agent"
    package_dir.mkdir()
    generate_package(
        package_dir,
        {
            "name": "Broken Tool Agent",
            "version": "1.0.0",
            "inherits": "core",
            "description": "Broken package",
            "tools": [{"import": "core.tools.filesystem:FileSystemTool"}],
            "workflows": ["planning"],
            "knowledge": ["docs"],
            "entrypoint": {"workflow": "planning"},
        },
    )

    with pytest.raises(ValueError, match="tools\\[0\\]\\.name"):
        validate_package(package_dir)


def test_load_registered_packages_missing_registry(tmp_path):
    assert load_registered_packages(tmp_path / "missing.json") == {}


# ---------------------------------------------------------------------------
# Unknown-tool warning + optional GitHub search
# ---------------------------------------------------------------------------

class TestUnknownToolHandling:
    """Tests for _register_known_tools behaviour on unknown tool names."""

    def test_unknown_tool_emits_warning(self):
        """An unknown tool name produces a RuntimeWarning."""
        tm = ToolManager()
        with pytest.warns(RuntimeWarning, match="unknown tool 'nonexistent_tool'"):
            _register_known_tools(tm, ["nonexistent_tool"])

    def test_warning_includes_helpful_message(self):
        """The warning tells the operator the tool won't be available."""
        tm = ToolManager()
        with pytest.warns(RuntimeWarning, match="will not be available at runtime"):
            _register_known_tools(tm, ["nonexistent_tool"])

    def test_known_tool_not_warned(self, recwarn):
        """A known tool does not emit a RuntimeWarning."""
        tm = ToolManager()
        _register_known_tools(tm, ["filesystem"])
        runtime_warnings = [w for w in recwarn.list if issubclass(w.category, RuntimeWarning)]
        assert runtime_warnings == []

    def test_github_search_not_called_without_env_var(self, monkeypatch):
        """_search_github_for_tool is NOT called when AGENT_TOOL_SEARCH is unset."""
        monkeypatch.delenv("AGENT_TOOL_SEARCH", raising=False)
        tm = ToolManager()
        with patch("builders.build_agent._search_github_for_tool") as mock_search:
            with pytest.warns(RuntimeWarning):
                _register_known_tools(tm, ["unknown_tool"])
            mock_search.assert_not_called()

    def test_github_search_called_when_env_var_set(self, monkeypatch):
        """_search_github_for_tool IS called when AGENT_TOOL_SEARCH=1."""
        monkeypatch.setenv("AGENT_TOOL_SEARCH", "1")
        tm = ToolManager()
        fake_results = [
            {"name": "org/tool-repo", "html_url": "https://github.com/org/tool-repo", "description": "A tool"}
        ]
        with patch("builders.build_agent._search_github_for_tool", return_value=fake_results) as mock_search:
            with pytest.warns(RuntimeWarning, match="org/tool-repo"):
                _register_known_tools(tm, ["unknown_tool"])
            mock_search.assert_called_once_with("unknown_tool")

    def test_github_search_no_results_message(self, monkeypatch):
        """When AGENT_TOOL_SEARCH=1 but no results, the warning says so."""
        monkeypatch.setenv("AGENT_TOOL_SEARCH", "1")
        tm = ToolManager()
        with patch("builders.build_agent._search_github_for_tool", return_value=[]):
            with pytest.warns(RuntimeWarning, match="no results"):
                _register_known_tools(tm, ["unknown_tool"])


class TestSearchGithubForTool:
    """Unit tests for _search_github_for_tool."""

    def test_returns_empty_list_on_network_error(self):
        """Network failures silently return an empty list."""
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = _search_github_for_tool("some_tool")
        assert result == []

    def test_parses_github_api_response(self):
        """Valid GitHub API JSON is parsed into the expected shape."""
        fake_payload = json.dumps({
            "items": [
                {
                    "full_name": "owner/repo",
                    "html_url": "https://github.com/owner/repo",
                    "description": "A test repo",
                }
            ]
        }).encode()

        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_payload
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_cm.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=mock_cm):
            result = _search_github_for_tool("some_tool")

        assert result == [
            {"name": "owner/repo", "html_url": "https://github.com/owner/repo", "description": "A test repo"}
        ]
