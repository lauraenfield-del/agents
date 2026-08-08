import json
from pathlib import Path

import pytest

from builders.build_agent import build_agent, load_registered_packages
from builders.generate_package import generate_package
from builders.register_package import register_package
from builders.validate_package import load_package_manifest, validate_package
from core.model.mock import MockModel
from core.model.openai_compatible import OpenAICompatibleModel
from core.runtime.agent import AgentRuntime

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
    assert "terminal" in runtime.tool_manager.list_tools()
    assert "web" in runtime.tool_manager.list_tools()


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


def test_load_registered_packages_missing_registry(tmp_path):
    assert load_registered_packages(tmp_path / "missing.json") == {}


def test_build_agent_uses_live_model_by_default():
    runtime = build_agent(PACKAGES_DIR / "coding")
    assert isinstance(runtime.model, OpenAICompatibleModel)


def test_build_agent_uses_mock_model_when_enabled(monkeypatch):
    monkeypatch.setenv("AGENTS_USE_MOCK_MODEL", "true")
    runtime = build_agent(PACKAGES_DIR / "coding")
    assert isinstance(runtime.model, MockModel)


def test_build_agent_rejects_unimplemented_tools(tmp_path):
    package_dir = tmp_path / "unsupported_tool_agent"
    manifest = {
        "name": "Unsupported Tool Agent",
        "version": "1.0.0",
        "inherits": "core",
        "description": "Agent with unsupported tool",
        "tools": ["made_up_tool"],
        "workflows": ["planning"],
        "knowledge": ["none"],
        "entrypoint": {"workflow": "unsupported_controller"},
    }
    generate_package(package_dir, manifest)

    with pytest.raises(ValueError, match="no implementation is available"):
        build_agent(package_dir)


def test_manifest_agent_runtime_returns_model_response(monkeypatch):
    monkeypatch.setenv("AGENTS_USE_MOCK_MODEL", "true")
    runtime = build_agent(PACKAGES_DIR / "research")
    result = runtime.start(user_input="Summarize this request.")
    assert "Original request: Summarize this request." in result
