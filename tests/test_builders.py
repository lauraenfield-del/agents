import json

import pytest

from builders.build_agent import build_agent, load_registered_packages
from builders.generate_package import generate_package
from builders.register_package import register_package
from builders.validate_package import load_package_manifest, validate_package
from core.runtime.agent import AgentRuntime


def test_validate_package_existing_manifest():
    manifest = validate_package("/home/runner/work/agents/agents/packages/autonomous")
    assert manifest["name"] == "Autonomous Agent"
    assert manifest["entrypoint"]["workflow"] == "autonomous_controller"


def test_register_package_updates_registry(tmp_path):
    registry_path = tmp_path / "package_index.json"

    entry = register_package(
        "/home/runner/work/agents/agents/packages/coding",
        registry_path=registry_path,
    )

    assert entry["name"] == "Coding Agent"
    with registry_path.open("r", encoding="utf-8") as registry_file:
        registry = json.load(registry_file)
    assert "coding" in registry


def test_build_agent_creates_runtime_with_known_tools():
    runtime = build_agent("/home/runner/work/agents/agents/packages/autonomous")

    assert isinstance(runtime, AgentRuntime)
    assert "filesystem" in runtime.tool_manager.list_tools()


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
